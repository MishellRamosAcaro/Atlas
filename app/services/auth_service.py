"""Authentication service for login, token management, and session handling."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.user_account_status import UserStatus
from app.repositories.files_repository import FilesRepository
from app.repositories.login_lockout_repository import LoginLockoutRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_account_status_repository import UserAccountStatusRepository
from app.services.email_service import EmailService
from app.services.jwt_service import JWTService

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _make_verification_code() -> str:
    """Generate a 6-digit numeric verification code."""
    return "".join(secrets.choice("0123456789") for _ in range(6))


class AuthService:
    """Service for authentication flows."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self._session = session
        self._user_repo = UserRepository(session)
        self._status_repo = UserAccountStatusRepository(session)
        self._refresh_repo = RefreshTokenRepository(session)
        self._lockout_repo = LoginLockoutRepository(session)
        self._files_repo = FilesRepository(session)
        self._email_service = EmailService()
        self._jwt_service = JWTService()

    def _hash_refresh_token(self, token: str) -> str:
        """Hash refresh token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    def _check_idle_timeout(self, token: RefreshToken) -> bool:
        """Check if refresh token has exceeded idle timeout."""
        idle_limit = datetime.now(timezone.utc) - timedelta(
            days=settings.idle_timeout_days
        )
        return token.last_used_at < idle_limit

    async def register(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        country_code: str,
        phone_number_normalized: str,
    ) -> User:
        """Register a new user with email/password; create status PENDING_VERIFICATION and send code."""
        existing = await self._user_repo.get_by_email(email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        password_hash = pwd_context.hash(password)
        user = await self._user_repo.create(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password_hash=password_hash,
            country_code=country_code,
            phone_number_normalized=phone_number_normalized,
        )
        await self._status_repo.create(user.id, status=UserStatus.PENDING_VERIFICATION)
        code = _make_verification_code()
        code_hash = pwd_context.hash(code)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=settings.verification_code_ttl_minutes)
        status_record = await self._status_repo.get_by_user_id(user.id)
        if status_record:
            status_record.verification_code_hash = code_hash
            status_record.verification_code_expires_at = expires_at
            status_record.verification_sent_at = now
            status_record.verification_attempts = 0
            await self._status_repo.update(status_record)
        await self._email_service.send_email(
            "verification_code",
            {"email": user.email, "code": code},
        )
        return user

    async def local_login(
        self,
        email: str,
        password: str,
        user_agent: str | None = None,
        client_ip: str | None = None,
    ) -> tuple[User, str]:
        """Process local (email/password) login. Returns (user, refresh_token)."""
        lockout = await self._lockout_repo.get_by_email(email)
        is_locked, minutes_left = self._lockout_repo.is_locked(lockout)
        if is_locked and minutes_left is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Try again in {minutes_left} minutes.",
            )

        user = await self._user_repo.get_by_email(email)
        if not user or not user.password_hash:
            await self._lockout_repo.record_failed_attempt(email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not pwd_context.verify(password, user.password_hash):
            await self._lockout_repo.record_failed_attempt(email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        await self._lockout_repo.clear(email)
        if not user.can_login:
            if user.account_status and user.account_status.status == UserStatus.PENDING_VERIFICATION:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": "Please verify your email before signing in.",
                        "code": "email_not_verified",
                    },
                ) from None
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is disabled or banned",
            )

        # Enforce max 2 sessions
        count = await self._refresh_repo.count_active_by_user(user.id)
        while count >= settings.max_sessions_per_user:
            await self._refresh_repo.delete_oldest_for_user(user.id)
            count = await self._refresh_repo.count_active_by_user(user.id)

        refresh_token_raw = secrets.token_urlsafe(64)
        refresh_token_hash = self._hash_refresh_token(refresh_token_raw)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_ttl_days
        )

        await self._refresh_repo.create(
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            client_ip=client_ip,
        )

        return user, refresh_token_raw

    async def refresh_tokens(
        self,
        refresh_token_raw: str,
        user_agent: str | None = None,
        client_ip: str | None = None,
    ) -> tuple[User, str]:
        """Rotate refresh token and return new (user, refresh_token)."""
        token_hash = self._hash_refresh_token(refresh_token_raw)
        token = await self._refresh_repo.get_by_token_hash(token_hash)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        # Check idle timeout
        if self._check_idle_timeout(token):
            await self._refresh_repo.delete_by_id(token.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired due to inactivity",
            )

        user = await self._user_repo.get_by_id(token.user_id)
        if not user or not user.can_login:
            await self._refresh_repo.delete_by_id(token.id)
            if user and user.account_status and user.account_status.status == UserStatus.PENDING_VERIFICATION:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": "Please verify your email before signing in.",
                        "code": "email_not_verified",
                    },
                ) from None
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is disabled or banned",
            )

        # Rotate: delete old, issue new
        await self._refresh_repo.delete_by_id(token.id)

        new_refresh_raw = secrets.token_urlsafe(64)
        new_refresh_hash = self._hash_refresh_token(new_refresh_raw)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_ttl_days
        )

        await self._refresh_repo.create(
            user_id=user.id,
            token_hash=new_refresh_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            client_ip=client_ip,
        )

        return user, new_refresh_raw

    async def logout(
        self, refresh_token_raw: str, global_logout: bool = False
    ) -> uuid.UUID | None:
        """Local or global logout. Returns user_id if global, else None."""
        if global_logout and refresh_token_raw:
            token_hash = self._hash_refresh_token(refresh_token_raw)
            token = await self._refresh_repo.get_by_token_hash(token_hash)
            if token:
                user_id = token.user_id
                await self._refresh_repo.delete_all_by_user(user_id)
                return user_id
        elif refresh_token_raw:
            token_hash = self._hash_refresh_token(refresh_token_raw)
            await self._refresh_repo.delete_by_token_hash(token_hash)
        return None

    def _normalize_email(self, email: str) -> str:
        """Normalize email for storage."""
        return email.strip().lower()

    async def verify_email(self, email: str, code: str) -> None:
        """Verify email with code; set ACTIVE and clear code on success."""
        key = self._normalize_email(email)
        user = await self._user_repo.get_by_email(key)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired code",
            )
        status_record = await self._status_repo.get_by_user_id(user.id)
        if not status_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired code",
            )
        if status_record.status == UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired code",
            )
        if status_record.verification_attempts >= settings.verification_max_attempts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired code",
            )
        now = datetime.now(timezone.utc)
        if not status_record.verification_code_expires_at or status_record.verification_code_expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired code",
            )
        if not status_record.verification_code_hash or not pwd_context.verify(
            code, status_record.verification_code_hash
        ):
            status_record.verification_attempts += 1
            await self._status_repo.update(status_record)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired code",
            )
        status_record.status = UserStatus.ACTIVE
        status_record.email_verified = True
        status_record.email_verified_at = now
        status_record.verification_code_hash = None
        status_record.verification_code_expires_at = None
        status_record.verification_attempts = 0
        await self._status_repo.update(status_record)

    async def resend_verification_code(self, email: str) -> int:
        """
        Resend verification code. Returns seconds until next resend allowed (0 if sent).
        Raises HTTPException on rate limit or if user already active.
        """
        key = self._normalize_email(email)
        user = await self._user_repo.get_by_email(key)
        status_record = await self._status_repo.get_by_user_id(user.id) if user else None
        if not user or not status_record:
            return 0
        if status_record.status == UserStatus.ACTIVE:
            return 0
        secs = self._status_repo.seconds_until_resend(
            status_record, settings.verification_resend_cooldown_minutes
        )
        if secs > 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many attempts. Try again in {secs} seconds.",
            )
        code = _make_verification_code()
        code_hash = pwd_context.hash(code)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=settings.verification_code_ttl_minutes)
        status_record.verification_code_hash = code_hash
        status_record.verification_code_expires_at = expires_at
        status_record.verification_sent_at = now
        status_record.verification_attempts = 0
        await self._status_repo.update(status_record)
        await self._email_service.send_email(
            "verification_code",
            {"email": user.email, "code": code},
        )
        return 0

    async def update_profile(
        self,
        user_id: uuid.UUID,
        *,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        country_code: str | None = None,
        phone_number_normalized: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[User, bool]:
        """Update user profile. Returns (user, email_changed). When email changes, sets
        PENDING_VERIFICATION, sends verification code to new email, and invalidates sessions.
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        email_changed = False
        if email is not None:
            normalized = self._normalize_email(email)
            if normalized != user.email:
                existing = await self._user_repo.get_by_email_excluding(
                    normalized, user_id
                )
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Email already registered",
                    )
                user.email = normalized
                email_changed = True
        if first_name is not None:
            user.first_name = first_name.strip()
        if last_name is not None:
            user.last_name = last_name.strip()
        if country_code is not None:
            user.country_code = country_code.strip()
        if phone_number_normalized is not None:
            user.phone_number_normalized = phone_number_normalized.strip().replace(
                " ", ""
            ).replace("-", "")
        if is_active is not None and user.account_status:
            user.account_status.status = (
                UserStatus.ACTIVE if is_active else UserStatus.DEACTIVATED
            )
            await self._status_repo.update(user.account_status)
        await self._user_repo.update(user)

        if email_changed and user.account_status:
            # Require re-verification of new email: set PENDING_VERIFICATION and send code
            code = _make_verification_code()
            code_hash = pwd_context.hash(code)
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(minutes=settings.verification_code_ttl_minutes)
            user.account_status.status = UserStatus.PENDING_VERIFICATION
            user.account_status.email_verified = False
            user.account_status.email_verified_at = None
            user.account_status.verification_code_hash = code_hash
            user.account_status.verification_code_expires_at = expires_at
            user.account_status.verification_sent_at = now
            user.account_status.verification_attempts = 0
            await self._status_repo.update(user.account_status)
            await self._email_service.send_email(
                "verification_code",
                {"email": user.email, "code": code},
            )
            await self._refresh_repo.delete_all_by_user(user_id)

        return user, email_changed

    async def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str,
    ) -> User:
        """Verify current password, set new hash, invalidate all sessions."""
        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Current password is incorrect",
            )
        if not pwd_context.verify(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Current password is incorrect",
            )
        user.password_hash = pwd_context.hash(new_password)
        await self._user_repo.update(user)
        await self._refresh_repo.delete_all_by_user(user_id)
        return user

    async def deactivate_account(self, user_id: uuid.UUID) -> None:
        """Set account status to DEACTIVATED and invalidate all sessions."""
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        if user.account_status:
            user.account_status.status = UserStatus.DEACTIVATED
            await self._status_repo.update(user.account_status)
        await self._refresh_repo.delete_all_by_user(user_id)

    async def delete_account(self, user_id: uuid.UUID, password: str) -> None:
        """Verify password, delete all user files from storage, then delete user."""
        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password is incorrect",
            )
        if not pwd_context.verify(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password is incorrect",
            )
        from app.infrastructure.storage import get_storage

        storage = get_storage()
        files = await self._files_repo.list_all_files_by_user(user_id)
        for file_record in files:
            try:
                storage.delete(file_record.stored_path)
            except Exception:
                pass
            if file_record.extracted_doc_path:
                try:
                    storage.delete(file_record.extracted_doc_path)
                except Exception:
                    pass
        await self._refresh_repo.delete_all_by_user(user_id)
        await self._lockout_repo.clear(user.email)
        await self._user_repo.delete_user(user_id)
