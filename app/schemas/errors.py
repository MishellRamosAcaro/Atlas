"""Standard error response schemas."""

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Single error detail."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable message")


class ErrorResponse(BaseModel):
    """Standard API error response."""

    error: ErrorDetail = Field(..., description="Error details")
