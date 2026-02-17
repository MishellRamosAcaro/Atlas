"""Request/response schemas for uploads API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UploadSuccessResponse(BaseModel):
    """Response for successful POST /uploads."""

    ok: bool = Field(True, description="Upload succeeded")
    file_id: UUID = Field(..., description="Id of the uploaded file")


class UploadListItem(BaseModel):
    """Single item in GET /uploads list."""

    file_id: UUID
    name: str = Field(..., description="Original filename")
    size: int = Field(..., description="Size in bytes")
    uploaded_at: datetime
    status: str = Field(..., description="CLEAN or PENDING_SCAN")


class UploadListResponse(BaseModel):
    """Response for GET /uploads."""

    items: list[UploadListItem] = Field(default_factory=list)


class UploadMetadataResponse(BaseModel):
    """Response for GET /uploads/{file_id} (metadata only)."""

    file_id: UUID
    name: str
    size: int
    content_type: str
    status: str
    uploaded_at: datetime
