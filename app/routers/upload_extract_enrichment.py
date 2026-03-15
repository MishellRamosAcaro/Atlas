"""Upload, extract and enrichment endpoint: upload file then run extraction and enrichment in one call."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.limiter import limiter
from app.middleware.auth import get_current_user_id
from app.repositories.files_repository import FilesRepository
from app.schemas.enrichments import EnrichmentResponse
from app.services.extraction_service import ExtractionService
from app.services.uploads_service import UploadsService
from app.services.enrichment_service import EnrichmentService

router = APIRouter()


@router.post(
    "",
    response_model=EnrichmentResponse,
    summary="Upload, extract and enrich a file",
    description="Upload a PDF file (multipart), run extraction and enrichment in one call. Returns enriched document and sections (file_id, source, document_type, technical_context, risk_level, audience, sections with heading, content, section_summary, keywords, etc.).",
)
@limiter.limit("10/minute")
async def upload_extract_and_enrich(
    request: Request,
    file: UploadFile = File(...),
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """Upload file, extract, enrich; return enriched document + sections in one response."""
    files_repo = FilesRepository(db)
    uploads_service = UploadsService(files_repo)
    extraction_service = ExtractionService(files_repo)
    enrichment_service = EnrichmentService(files_repo)

    file_id, _ = await uploads_service.upload_file(user_id, file)
    await extraction_service.extract_from_file(file_id, user_id)
    enrichment_payload = await enrichment_service.enrich_file(
        file_id, user_id, max_concurrent=3
    )

    document = dict(enrichment_payload.get("document") or {})
    document.setdefault("file_id", str(file_id))
    sections = list(enrichment_payload.get("sections") or [])

    return EnrichmentResponse(document=document, sections=sections)
