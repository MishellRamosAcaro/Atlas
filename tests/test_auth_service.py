"""Tests for auth service."""

import pytest
from fastapi import HTTPException
from passlib.context import CryptContext

from app.models.user_account_status import UserStatus
from app.repositories.user_repository import UserRepository
from app.repositories.user_account_status_repository import UserAccountStatusRepository
from app.services.auth_service import AuthService

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_REGISTER_PARAMS = {
    "country_code": "+34",
    "phone_number_normalized": "34600000000",
}


@pytest.mark.asyncio
async def test_register_creates_user(db_session, monkeypatch):
    """Register creates user with hashed password and sends verification email."""

    class MockEmailService:
        async def send_email(self, template_id: str, context: dict):
            pass

    monkeypatch.setattr(
        "app.services.auth_service.EmailService",
        MockEmailService,
    )
    auth_service = AuthService(db_session)
    user = await auth_service.register(
        email="new@example.com",
        password="password123",
        first_name="New",
        last_name="User",
        **_REGISTER_PARAMS,
    )
    await db_session.commit()
    assert user.email == "new@example.com"
    assert user.first_name == "New"
    assert user.last_name == "User"
    assert user.name == "New User"
    assert user.password_hash is not None
    assert pwd_context.verify("password123", user.password_hash)
    assert user.roles == ["user"]
    assert user.country_code == "+34"
    assert user.phone_number_normalized == "34600000000"


@pytest.mark.asyncio
async def test_register_duplicate_email_raises(db_session):
    """Register with existing email raises 409."""
    user_repo = UserRepository(db_session)
    status_repo = UserAccountStatusRepository(db_session)
    user = await user_repo.create(
        email="existing@example.com",
        first_name="Existing",
        last_name="User",
        password_hash="hash",
        country_code="+1",
        phone_number_normalized="10000000000",
    )
    await status_repo.create(user.id, status=UserStatus.ACTIVE)
    await db_session.commit()

    auth_service = AuthService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.register(
            email="existing@example.com",
            password="password",
            first_name="Other",
            last_name="User",
            **_REGISTER_PARAMS,
        )
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_local_login_success(db_session):
    """Local login returns user and refresh token after email is verified."""
    auth_service = AuthService(db_session)
    await auth_service.register(
        email="login@example.com",
        password="secret123",
        first_name="Login",
        last_name="User",
        **_REGISTER_PARAMS,
    )
    await db_session.commit()
    status_repo = UserAccountStatusRepository(db_session)
    user_repo = UserRepository(db_session)
    user = await user_repo.get_by_email("login@example.com")
    status_record = await status_repo.get_by_user_id(user.id)
    status_record.status = UserStatus.ACTIVE
    status_record.email_verified = True
    await status_repo.update(status_record)
    await db_session.commit()

    user, refresh_token = await auth_service.local_login(
        email="login@example.com",
        password="secret123",
    )
    assert user.email == "login@example.com"
    assert refresh_token is not None
    assert len(refresh_token) > 0


@pytest.mark.asyncio
async def test_local_login_wrong_password_raises(db_session):
    """Local login with wrong password raises 401."""
    auth_service = AuthService(db_session)
    await auth_service.register(
        email="login@example.com",
        password="secret123",
        first_name="Login",
        last_name="User",
        **_REGISTER_PARAMS,
    )
    await db_session.commit()
    status_repo = UserAccountStatusRepository(db_session)
    user_repo = UserRepository(db_session)
    user = await user_repo.get_by_email("login@example.com")
    status_record = await status_repo.get_by_user_id(user.id)
    status_record.status = UserStatus.ACTIVE
    await status_repo.update(status_record)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.local_login(
            email="login@example.com",
            password="wrong",
        )
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_local_login_lockout_after_max_failed_attempts(db_session, monkeypatch):
    """After max failed attempts, login returns 429 lockout."""
    from app.repositories.login_lockout_repository import settings as lockout_settings

    monkeypatch.setattr(lockout_settings, "max_failed_login_attempts", 3)
    monkeypatch.setattr(lockout_settings, "lockout_minutes", 15)

    auth_service = AuthService(db_session)
    await auth_service.register(
        email="lockout@example.com",
        password="secret123",
        first_name="Lockout",
        last_name="User",
        **_REGISTER_PARAMS,
    )
    await db_session.commit()
    status_repo = UserAccountStatusRepository(db_session)
    user_repo = UserRepository(db_session)
    user = await user_repo.get_by_email("lockout@example.com")
    status_record = await status_repo.get_by_user_id(user.id)
    status_record.status = UserStatus.ACTIVE
    await status_repo.update(status_record)
    await db_session.commit()

    for _ in range(3):
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.local_login(
                email="lockout@example.com",
                password="wrong",
            )
        assert exc_info.value.status_code == 401

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.local_login(
            email="lockout@example.com",
            password="wrong",
        )
    assert exc_info.value.status_code == 429
    assert "Too many failed" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_logout_local_invalidates_token(db_session):
    """Local logout invalidates refresh token."""
    auth_service = AuthService(db_session)
    await auth_service.register(
        email="logout@example.com",
        password="pass",
        first_name="Logout",
        last_name="User",
        **_REGISTER_PARAMS,
    )
    await db_session.commit()
    status_repo = UserAccountStatusRepository(db_session)
    user_repo = UserRepository(db_session)
    user = await user_repo.get_by_email("logout@example.com")
    status_record = await status_repo.get_by_user_id(user.id)
    status_record.status = UserStatus.ACTIVE
    await status_repo.update(status_record)
    await db_session.commit()
    _, refresh_token = await auth_service.local_login(
        email="logout@example.com",
        password="pass",
    )

    await auth_service.logout(refresh_token_raw=refresh_token, global_logout=False)
    await db_session.commit()

    with pytest.raises(HTTPException):
        await auth_service.refresh_tokens(refresh_token_raw=refresh_token)


@pytest.mark.asyncio
async def test_login_pending_verification_returns_403(db_session, monkeypatch):
    """Login with user in PENDING_VERIFICATION returns 403 with email_not_verified."""

    class MockEmailService:
        async def send_email(self, template_id: str, context: dict):
            pass

    monkeypatch.setattr(
        "app.services.auth_service.EmailService",
        MockEmailService,
    )
    auth_service = AuthService(db_session)
    await auth_service.register(
        email="pending@example.com",
        password="secret123",
        first_name="Pending",
        last_name="User",
        **_REGISTER_PARAMS,
    )
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.local_login(
            email="pending@example.com",
            password="secret123",
        )
    assert exc_info.value.status_code == 403
    assert isinstance(exc_info.value.detail, dict)
    assert exc_info.value.detail.get("code") == "email_not_verified"


@pytest.mark.asyncio
async def test_verify_email_success(db_session, monkeypatch):
    """Verify email with correct code sets user to ACTIVE."""

    class MockEmailService:
        async def send_email(self, template_id: str, context: dict):
            pass

    monkeypatch.setattr(
        "app.services.auth_service.EmailService",
        MockEmailService,
    )
    auth_service = AuthService(db_session)
    await auth_service.register(
        email="verify@example.com",
        password="secret123",
        first_name="Verify",
        last_name="User",
        **_REGISTER_PARAMS,
    )
    await db_session.commit()
    status_repo = UserAccountStatusRepository(db_session)
    user_repo = UserRepository(db_session)
    user = await user_repo.get_by_email("verify@example.com")
    status_record = await status_repo.get_by_user_id(user.id)
    code = "123456"
    from passlib.context import CryptContext

    status_record.verification_code_hash = CryptContext(
        schemes=["bcrypt"], deprecated="auto"
    ).hash(code)
    from datetime import datetime, timedelta, timezone

    status_record.verification_code_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=15
    )
    await status_repo.update(status_record)
    await db_session.commit()

    await auth_service.verify_email("verify@example.com", code)
    await db_session.commit()

    status_record = await status_repo.get_by_user_id(user.id)
    assert status_record.status == UserStatus.ACTIVE
    assert status_record.email_verified is True
    assert status_record.verification_code_hash is None
