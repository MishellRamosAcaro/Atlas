"""Cookie utilities for auth tokens."""

from fastapi import Response

from app.config import get_settings

settings = get_settings()

ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    """Set HttpOnly Secure cookies for access and refresh tokens."""
    # Access token: 15 min
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_same_site,
        max_age=settings.access_token_ttl_minutes * 60,
        path="/",
        domain=settings.cookie_domain,
    )
    # Refresh token: 30 days
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_same_site,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        path="/",
        domain=settings.cookie_domain,
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear auth cookies (logout)."""
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE,
        path="/",
        domain=settings.cookie_domain,
    )
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE,
        path="/",
        domain=settings.cookie_domain,
    )
