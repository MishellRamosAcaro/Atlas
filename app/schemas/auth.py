"""Authentication request/response schemas."""

import re
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

# E.164: + followed by 1-9 and 1-14 digits
E164_FULL_PATTERN = re.compile(r"^\+[1-9]\d{1,14}$")


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
    country_code: str = Field(..., description="Phone country code (e.g. +34)")
    phone_number_normalized: str = Field(
        ...,
        description="Phone number in E.164 format without + (e.g. 34612345678)",
    )
    accept_terms: bool = Field(..., description="User accepts terms of service")
    accept_privacy: bool = Field(..., description="User accepts privacy policy")

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        if not v or not v.startswith("+") or len(v) < 2 or len(v) > 5:
            raise ValueError("Invalid country code (e.g. +34)")
        if not re.match(r"^\+[1-9]\d{0,4}$", v):
            raise ValueError("Invalid country code format")
        return v.strip()

    @field_validator("phone_number_normalized")
    @classmethod
    def validate_phone_e164(cls, v: str) -> str:
        digits = v.strip().replace(" ", "").replace("-", "")
        if not digits.isdigit() or len(digits) < 9 or len(digits) > 15:
            raise ValueError("Invalid phone number (E.164)")
        return digits

    @model_validator(mode="after")
    def require_acceptances(self):
        if not self.accept_terms or not self.accept_privacy:
            raise ValueError("You must accept the terms and privacy policy")
        return self


class VerifyEmailRequest(BaseModel):
    """Request for POST /auth/verify-email."""

    email: EmailStr = Field(..., description="User email")
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$", description="6-digit verification code")


class ResendVerificationRequest(BaseModel):
    """Request for POST /auth/resend-verification-code."""

    email: EmailStr = Field(..., description="User email")


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
    country_code: str | None = Field(None, description="Phone country code (e.g. +34)")
    phone_number_normalized: str | None = Field(
        None,
        description="Phone number in E.164 format without + (e.g. 34612345678)",
    )
    is_active: bool | None = Field(None, description="Account active flag")

    @field_validator("country_code")
    @classmethod
    def validate_country_code_optional(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        v = v.strip()
        if not re.match(r"^\+[1-9]\d{0,4}$", v):
            raise ValueError("Invalid country code (e.g. +34)")
        return v

    @field_validator("phone_number_normalized")
    @classmethod
    def validate_phone_optional(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        digits = v.strip().replace(" ", "").replace("-", "")
        if not digits.isdigit() or len(digits) < 9 or len(digits) > 15:
            raise ValueError("Invalid phone number (E.164)")
        return digits

    @model_validator(mode="after")
    def at_least_one_field(self):
        if (
            self.email is None
            and self.first_name is None
            and self.last_name is None
            and self.country_code is None
            and self.phone_number_normalized is None
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
    """Response for GET /auth/me. PATCH /auth/me may add email_pending_verification when email was changed."""

    id: UUID
    email: str
    name: str
    first_name: str
    last_name: str
    country_code: str
    phone_number_normalized: str
    is_active: bool
    roles: list[str]
    email_pending_verification: bool = False
