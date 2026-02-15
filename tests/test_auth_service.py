"""Tests for auth service."""

import pytest
from fastapi import HTTPException
from passlib.context import CryptContext

from app.models.user import User
from app.repositories.oauth_identity_repository import OAuthIdentityRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.mark.asyncio
async def test_register_creates_user(db_session):
    """Register creates user with hashed password."""
    auth_service = AuthService(db_session)
    user = await auth_service.register(
        email="new@example.com",
        password="password123",
        first_name="New",
        last_name="User",
    )
    await db_session.commit()
    assert user.email == "new@example.com"
    assert user.first_name == "New"
    assert user.last_name == "User"
    assert user.name == "New User"
    assert user.password_hash is not None
    assert pwd_context.verify("password123", user.password_hash)
    assert user.roles == ["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email_raises(db_session):
    """Register with existing email raises 409."""
    user_repo = UserRepository(db_session)
    await user_repo.create(
        email="existing@example.com",
        first_name="Existing",
        last_name="User",
        password_hash="hash",
    )
    await db_session.commit()

    auth_service = AuthService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.register(
            email="existing@example.com",
            password="password",
            first_name="Other",
            last_name="User",
        )
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_local_login_success(db_session):
    """Local login returns user and refresh token."""
    auth_service = AuthService(db_session)
    await auth_service.register(
        email="login@example.com",
        password="secret123",
        first_name="Login",
        last_name="User",
    )
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
    )
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.local_login(
            email="login@example.com",
            password="wrong",
        )
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_logout_local_invalidates_token(db_session):
    """Local logout invalidates refresh token."""
    auth_service = AuthService(db_session)
    await auth_service.register(
        email="logout@example.com",
        password="pass",
        first_name="Logout",
        last_name="User",
    )
    await db_session.commit()
    _, refresh_token = await auth_service.local_login(
        email="logout@example.com",
        password="pass",
    )

    await auth_service.logout(refresh_token_raw=refresh_token, global_logout=False)
    await db_session.commit()

    with pytest.raises(HTTPException):
        await auth_service.refresh_tokens(refresh_token_raw=refresh_token)
