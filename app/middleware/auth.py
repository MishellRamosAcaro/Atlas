"""Authentication middleware and dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import Cookie, HTTPException, status

from app.services.jwt_service import JWTService

ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"

jwt_service = JWTService()


async def get_current_user_id(
    access_token: str | None = Cookie(default=None, alias="access_token"),
) -> UUID:
    """Dependency: extract and validate access token from cookie, return user_id."""
    token = access_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    payload = jwt_service.decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    try:
        return UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )


async def get_refresh_token_from_cookie(
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
) -> str | None:
    """Dependency: extract refresh token from cookie."""
    return refresh_token
