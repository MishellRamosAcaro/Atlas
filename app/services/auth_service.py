"""Authentication service for login, token management, and session handling."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.oauth_identity_repository import OAuthIdentityRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.jwt_service import JWTService

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication flows."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self._session = session
        self._user_repo = UserRepository(session)
        self._oauth_repo = OAuthIdentityRepository(session)
        self._refresh_repo = RefreshTokenRepository(session)
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

    async def validate_google_id_token(self, id_token: str) -> dict:
        """Validate Google id_token and return payload.

        Raises HTTPException if token is invalid or email is missing.
        """
        try:
            payload = google_id_token.verify_oauth2_token(
                id_token,
                google_requests.Request(),
                settings.google_client_id,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google ID token",
            ) from e

        email = payload.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google account must provide an email",
            )

        return payload

    async def google_login(
        self,
        id_token: str,
        user_agent: str | None = None,
        client_ip: str | None = None,
    ) -> tuple[User, str]:
        """Process Google OAuth login. Returns (user, refresh_token)."""
        payload = await self.validate_google_id_token(id_token)
        email = payload["email"]
        name = payload.get("name") or email.split("@")[0]
        provider_user_id = payload.get("sub", "")
        provider = "google"

        # Find existing OAuth identity or user
        oauth_identity = await self._oauth_repo.get_by_provider_user(
            provider, provider_user_id
        )
        if oauth_identity:
            user = await self._user_repo.get_by_id(oauth_identity.user_id)
            if not user or not user.can_login:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is disabled or banned",
                )
        else:
            # New user or link to existing user by email
            user = await self._user_repo.get_by_email(email)
            if user:
                if not user.can_login:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="User is disabled or banned",
                    )
                await self._oauth_repo.create(user.id, provider, provider_user_id)
            else:
                user = await self._user_repo.create(
                    email=email,
                    name=name,
                    password_hash=None,
                )
                await self._oauth_repo.create(user.id, provider, provider_user_id)

        # Enforce max 2 sessions
        count = await self._refresh_repo.count_active_by_user(user.id)
        while count >= settings.max_sessions_per_user:
            await self._refresh_repo.delete_oldest_for_user(user.id)
            count = await self._refresh_repo.count_active_by_user(user.id)

        # Issue tokens
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

    async def register(
        self, email: str, password: str, name: str | None = None
    ) -> User:
        """Register a new user with email/password."""
        existing = await self._user_repo.get_by_email(email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        password_hash = pwd_context.hash(password)
        display_name = name or email.split("@")[0]
        user = await self._user_repo.create(
            email=email,
            name=display_name,
            password_hash=password_hash,
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
        user = await self._user_repo.get_by_email(email)
        if not user or not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not pwd_context.verify(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.can_login:
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
