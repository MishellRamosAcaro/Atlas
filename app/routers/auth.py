"""Authentication endpoints."""

import base64
import hashlib
import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.limiter import limiter
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user_id, get_refresh_token_from_cookie
from app.middleware.cookies import clear_auth_cookies, set_auth_cookies
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    GoogleCallbackRequest,
    GoogleStartResponse,
    MeResponse,
    RegisterRequest,
    TokenRequest,
)
from app.services.auth_service import AuthService
from app.services.jwt_service import JWTService

router = APIRouter()
settings = get_settings()
jwt_service = JWTService()


def _make_code_challenge(code_verifier: str) -> str:
    """Generate S256 PKCE code challenge."""
    digest = hashlib.sha256(code_verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


@router.get(
    "/google/start",
    response_model=GoogleStartResponse,
    summary="Start Google OAuth flow",
    description="Returns OAuth URL, state, and PKCE code_verifier for frontend.",
)
@limiter.limit("30/minute")
async def google_start(request: Request) -> GoogleStartResponse:
    """Return Google OAuth authorization URL and PKCE params for frontend redirect."""
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = _make_code_challenge(code_verifier)

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    authorization_url = f"https://accounts.google.com/o/oauth2/v2/auth?{qs}"

    return GoogleStartResponse(
        authorization_url=authorization_url,
        state=state,
        code_verifier=code_verifier,
    )


@router.post(
    "/google/callback",
    summary="Complete Google OAuth login",
    description="Accepts id_token from frontend, validates, and issues auth cookies.",
)
@limiter.limit("30/minute")
async def google_callback(
    body: GoogleCallbackRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Validate Google id_token and issue access + refresh tokens via cookies."""
    auth_service = AuthService(db)
    user, refresh_token = await auth_service.google_login(
        id_token=body.id_token,
        user_agent=request.headers.get("User-Agent"),
        client_ip=request.client.host if request.client else None,
    )
    access_token = jwt_service.create_access_token(user)
    set_auth_cookies(response, access_token, refresh_token)
    return {"message": "Login successful"}


@router.post(
    "/register",
    summary="Register new user",
    description="Create account for local login (email/password).",
)
@limiter.limit("10/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Register a new user with email and password."""
    auth_service = AuthService(db)
    await auth_service.register(
        email=body.email,
        password=body.password,
        first_name=body.first_name,
        last_name=body.last_name,
    )
    return {"message": "Registration successful"}


@router.post(
    "/token",
    summary="Obtain or refresh tokens",
    description="Password grant (local login) or refresh_token grant.",
)
@limiter.limit("30/minute")
async def token(
    body: TokenRequest | None,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token_cookie: Annotated[str | None, Depends(get_refresh_token_from_cookie)],
) -> dict:
    """Handle password grant (local login) or refresh_token grant (token rotation)."""
    auth_service = AuthService(db)

    if body and body.grant_type == "password":
        if not body.email or not body.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email and password required for password grant",
            )
        user, refresh_token = await auth_service.local_login(
            email=body.email,
            password=body.password,
            user_agent=request.headers.get("User-Agent"),
            client_ip=request.client.host if request.client else None,
        )
    elif (body and body.grant_type == "refresh_token") or refresh_token_cookie:
        refresh_raw = refresh_token_cookie
        if not refresh_raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="refresh_token cookie required for refresh grant",
            )
        user, refresh_token = await auth_service.refresh_tokens(
            refresh_token_raw=refresh_raw,
            user_agent=request.headers.get("User-Agent"),
            client_ip=request.client.host if request.client else None,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="grant_type password or refresh_token required",
        )

    access_token = jwt_service.create_access_token(user)
    set_auth_cookies(response, access_token, refresh_token)
    return {"message": "Token issued"}


@router.post(
    "/logout",
    summary="Logout",
    description="Local logout (single device) or global logout (all devices).",
)
@limiter.limit("30/minute")
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token_cookie: Annotated[str | None, Depends(get_refresh_token_from_cookie)],
    global_logout: bool = False,
) -> dict:
    """Invalidate refresh token(s) and clear cookies."""
    auth_service = AuthService(db)
    await auth_service.logout(
        refresh_token_raw=refresh_token_cookie or "",
        global_logout=global_logout,
    )
    clear_auth_cookies(response)
    return {"message": "Logged out"}


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get current user",
    description="Returns current user profile from access token.",
)
async def me(
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MeResponse:
    """Return current user profile."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return MeResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        roles=user.roles,
    )
