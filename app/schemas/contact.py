"""Contact form request/response schemas."""

from pydantic import BaseModel, EmailStr, Field


class ContactRequest(BaseModel):
    """Request body for POST /contact."""

    name: str = Field(..., min_length=2, max_length=100, description="Contact name")
    email: EmailStr = Field(..., description="Contact email")
    company: str = Field(..., min_length=2, max_length=100, description="Company name")
    message: str = Field(..., min_length=10, max_length=1000, description="Message")
    honeypot: str = Field(default="", description="Must be empty; if filled, backend returns 400 (anti-spam)")


class ContactResponse(BaseModel):
    """Success response for POST /contact."""

    message: str = Field(
        default="Thank you. We will get back to you soon.",
        description="Confirmation message",
    )
