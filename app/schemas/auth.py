"""Authentication request/response schemas."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class GoogleStartResponse(BaseModel):
    """Response for GET /auth/google/start."""

    authorization_url: str = Field(..., description="Google OAuth authorization URL")
    state: str = Field(..., description="State for CSRF protection")
    code_verifier: str = Field(..., description="PKCE code verifier for frontend")


class GoogleCallbackRequest(BaseModel):
    """Request for POST /auth/google/callback."""

    id_token: str = Field(..., description="Google id_token from OAuth flow")
    state: str = Field(..., description="State from /auth/google/start")


class RegisterRequest(BaseModel):
    """Request for POST /auth/register."""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="Password")
    name: str | None = Field(None, description="Display name")


class TokenRequest(BaseModel):
    """Request for POST /auth/token (password grant)."""

    grant_type: str = Field(..., description="Grant type: password or refresh_token")
    email: EmailStr | None = Field(None, description="Email for password grant")
    password: str | None = Field(None, description="Password for password grant")


class MeResponse(BaseModel):
    """Response for GET /auth/me."""

    id: UUID
    email: str
    name: str
    roles: list[str]
