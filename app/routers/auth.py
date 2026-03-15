"""Authentication endpoints."""

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
from app.models.user_account_status import UserStatus
from app.schemas.auth import (
    DeleteAccountRequest,
    MeResponse,
    PatchMeRequest,
    PatchPasswordRequest,
    RegisterRequest,
    ResendVerificationRequest,
    TokenRequest,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService
from app.services.jwt_service import JWTService

router = APIRouter()
settings = get_settings()
jwt_service = JWTService()


@router.post(
    "/register",
    summary="Register new user",
    description="Create account for local login (email/password). Sends verification email.",
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Register a new user with email, password, and phone. Sends 6-digit verification code."""
    auth_service = AuthService(db)
    await auth_service.register(
        email=body.email,
        password=body.password,
        first_name=body.first_name,
        last_name=body.last_name,
        country_code=body.country_code,
        phone_number_normalized=body.phone_number_normalized,
    )
    return {
        "message": "Registration successful. Check your email for the verification code."
    }


@router.post(
    "/verify-email",
    summary="Verify email with code",
    description="Confirm email with 6-digit code; activates account.",
)
@limiter.limit("3/minute")
async def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Verify email with code; on success user can log in."""
    auth_service = AuthService(db)
    await auth_service.verify_email(email=body.email, code=body.code)
    return {"message": "Email verified. You can now sign in."}


@router.post(
    "/resend-verification-code",
    summary="Resend verification code",
    description="Send a new 6-digit code (rate limited per email).",
)
@limiter.limit("2/minute")
async def resend_verification_code(
    request: Request,
    body: ResendVerificationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Resend verification code to email."""
    auth_service = AuthService(db)
    await auth_service.resend_verification_code(email=body.email)
    return {"message": "Verification code sent."}


@router.post(
    "/token",
    summary="Obtain or refresh tokens",
    description="Password grant (local login) or refresh_token grant.",
)
@limiter.limit("20/minute")
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
    is_active = (
        user.account_status is not None
        and user.account_status.status == UserStatus.ACTIVE
    )
    return MeResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        first_name=user.first_name,
        last_name=user.last_name,
        country_code=user.country_code,
        phone_number_normalized=user.phone_number_normalized,
        is_active=is_active,
        roles=user.roles,
        email_pending_verification=False,
    )


@router.patch(
    "/me",
    response_model=MeResponse,
    summary="Update current user profile",
    description="Update email, name, phone, or is_active. If email changes, verification code is sent and sessions are invalidated.",
)
async def patch_me(
    body: PatchMeRequest,
    response: Response,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MeResponse:
    """Update current user profile. When email changes, set PENDING_VERIFICATION and send code to new email."""
    auth_service = AuthService(db)
    user, email_changed = await auth_service.update_profile(
        user_id,
        email=body.email.strip().lower() if body.email else None,
        first_name=body.first_name.strip() if body.first_name else None,
        last_name=body.last_name.strip() if body.last_name else None,
        country_code=body.country_code.strip() if body.country_code else None,
        phone_number_normalized=(
            body.phone_number_normalized.strip()
            if body.phone_number_normalized
            else None
        ),
        is_active=body.is_active,
    )
    if email_changed:
        clear_auth_cookies(response)
    is_active = (
        user.account_status is not None
        and user.account_status.status == UserStatus.ACTIVE
    )
    return MeResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        first_name=user.first_name,
        last_name=user.last_name,
        country_code=user.country_code,
        phone_number_normalized=user.phone_number_normalized,
        is_active=is_active,
        roles=user.roles,
        email_pending_verification=email_changed,
    )


@router.patch(
    "/me/password",
    summary="Change password",
    description="Set new password and invalidate all sessions.",
)
async def patch_me_password(
    body: PatchPasswordRequest,
    response: Response,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Change password; invalidate all sessions and clear cookies."""
    auth_service = AuthService(db)
    await auth_service.change_password(
        user_id,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    clear_auth_cookies(response)
    return {"message": "Password updated. Please log in again."}


@router.post(
    "/me/deactivate",
    summary="Deactivate account",
    description="Set account inactive and log out all sessions.",
)
async def post_me_deactivate(
    response: Response,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Deactivate account and clear cookies."""
    auth_service = AuthService(db)
    await auth_service.deactivate_account(user_id)
    clear_auth_cookies(response)
    return {"message": "Account deactivated. You have been logged out."}


@router.delete(
    "/me",
    summary="Delete account",
    description="Delete account and all associated data. Requires password confirmation.",
)
async def delete_me(
    body: DeleteAccountRequest,
    response: Response,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Delete account, all files, and clear cookies."""
    auth_service = AuthService(db)
    await auth_service.delete_account(user_id, body.password)
    clear_auth_cookies(response)
    return {"message": "Account and all associated data have been deleted."}
