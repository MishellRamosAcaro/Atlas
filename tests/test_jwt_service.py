"""Tests for JWT service."""

import uuid

import pytest

from app.models.user import User
from app.services.jwt_service import JWTService


@pytest.fixture
def jwt_service():
    """JWT service instance."""
    return JWTService()


@pytest.fixture
def sample_user():
    """Sample user for JWT tests."""
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password_hash=None,
        roles=["user"],
        is_active=True,
        is_banned=False,
    )


def test_create_access_token(jwt_service: JWTService, sample_user: User):
    """Create access token includes sub, email, roles."""
    token = jwt_service.create_access_token(sample_user)
    assert token is not None
    assert isinstance(token, str)
    payload = jwt_service.decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == str(sample_user.id)
    assert payload["email"] == sample_user.email
    assert payload["roles"] == ["user"]
    assert "iat" in payload
    assert "exp" in payload


def test_decode_invalid_token_returns_none(jwt_service: JWTService):
    """Invalid token returns None."""
    assert jwt_service.decode_access_token("invalid") is None
    assert jwt_service.decode_access_token("") is None
