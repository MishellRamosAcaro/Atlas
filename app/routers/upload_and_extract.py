"""Upload and extractions endpoint: upload file then run extraction in one call."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.limiter import limiter
from app.middleware.auth import get_current_user_id
from app.repositories.files_repository import FilesRepository
from app.schemas.extractions import ExtractedDocumentFields, ExtractedDocumentResponse
from app.services.extraction_service import ExtractionService
from app.services.uploads_service import UploadsService

router = APIRouter()


def _document_to_fields(document: dict) -> ExtractedDocumentFields:
    """Build ExtractedDocumentFields from raw document dict (no sections)."""
    return ExtractedDocumentFields(
        file_id=str(document["file_id"]) if document.get("file_id") is not None else None,
        source=document.get("source"),
        document_type=document.get("document_type"),
        technical_context=document.get("technical_context"),
        risk_level=document.get("risk_level"),
        audience=document.get("audience") or [],
        state=document.get("state"),
        effective_date=document.get("effective_date"),
        owner_team=document.get("owner_team"),
    )


@router.post(
    "",
    response_model=ExtractedDocumentResponse,
    summary="Upload and extract",
    description="Upload a PDF file (multipart) and run extraction in one call. Returns only document fields (file_id, source, document_type, technical_context, risk_level, audience, state, effective_date, owner_team). Sections are not returned.",
)
@limiter.limit("10/minute")
async def upload_and_extract(
    request: Request,
    file: UploadFile = File(...),
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """Call uploads (upload_file) then extractions (extract_from_file); return document fields only (no sections)."""
    files_repo = FilesRepository(db)
    uploads_service = UploadsService(files_repo)
    extraction_service = ExtractionService(files_repo)

    file_id, _ = await uploads_service.upload_file(user_id, file)
    payload = await extraction_service.extract_from_file(file_id, user_id)
    document = payload["document"]
    fields = _document_to_fields(document)
    return ExtractedDocumentResponse(document=fields)
