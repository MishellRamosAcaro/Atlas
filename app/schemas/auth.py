"""Authentication request/response schemas."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class GoogleStartResponse(BaseModel):
    """Response for GET /auth/google/start."""

    authorization_url: str = Field(..., description="Google OAuth authorization URL")
    state: str = Field(..., description="State for CSRF protection")
    code_verifier: str = Field(..., description="PKCE code verifier for frontend")


class GoogleCallbackRequest(BaseModel):
    """Request for POST /auth/google/callback."""

    id_token: str = Field(..., description="Google id_token from OAuth flow")
    state: str = Field(..., description="State from /auth/google/start")


def _normalize_email(v: str) -> str:
    """Normalize email for storage (lowercase, strip)."""
    return v.strip().lower() if isinstance(v, str) else v


def _name_validator(v: str) -> str:
    """Validate and sanitize first/last name (strip, length 2-100)."""
    if not isinstance(v, str):
        return v
    s = v.strip()
    if len(s) < 2 or len(s) > 100:
        raise ValueError("Must be between 2 and 100 characters")
    return s


class RegisterRequest(BaseModel):
    """Request for POST /auth/register."""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="Password")
    first_name: str = Field(..., min_length=2, max_length=100, description="First name")
    last_name: str = Field(..., min_length=2, max_length=100, description="Last name")


class TokenRequest(BaseModel):
    """Request for POST /auth/token (password grant)."""

    grant_type: str = Field(..., description="Grant type: password or refresh_token")
    email: EmailStr | None = Field(None, description="Email for password grant")
    password: str | None = Field(None, description="Password for password grant")


class PatchMeRequest(BaseModel):
    """Request for PATCH /auth/me (all fields optional; at least one required)."""

    email: EmailStr | None = Field(None, description="User email")
    first_name: str | None = Field(None, min_length=2, max_length=100, description="First name")
    last_name: str | None = Field(None, min_length=2, max_length=100, description="Last name")
    is_active: bool | None = Field(None, description="Account active flag")

    @model_validator(mode="after")
    def at_least_one_field(self):
        if (
            self.email is None
            and self.first_name is None
            and self.last_name is None
            and self.is_active is None
        ):
            raise ValueError("At least one field must be provided")
        return self


class PatchPasswordRequest(BaseModel):
    """Request for PATCH /auth/me/password."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class DeleteAccountRequest(BaseModel):
    """Request for DELETE /auth/me (password confirmation)."""

    password: str = Field(..., description="Current password to confirm account deletion")


class MeResponse(BaseModel):
    """Response for GET /auth/me."""

    id: UUID
    email: str
    name: str
    first_name: str
    last_name: str
    is_active: bool
    roles: list[str]
