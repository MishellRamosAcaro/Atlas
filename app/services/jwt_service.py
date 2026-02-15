"""JWT service for access token creation and validation."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.config import get_settings
from app.models.user import User

settings = get_settings()


class JWTService:
    """Service for JWT access token operations."""

    def create_access_token(self, user: User) -> str:
        """Create JWT access token for user."""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=settings.access_token_ttl_minutes)
        payload: dict[str, Any] = {
            "sub": str(user.id),
            "email": user.email,
            "roles": user.roles,
            "iat": now,
            "exp": expires_at,
        }
        return jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    def decode_access_token(self, token: str) -> dict[str, Any] | None:
        """Decode and validate JWT access token. Returns payload or None."""
        try:
            return jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
        except jwt.PyJWTError:
            return None
