"""Enrichments endpoint: run LLM enrichment on an extracted file."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user_id
from app.repositories.files_repository import FilesRepository
from app.schemas.enrichments import EnrichmentRequestBody, EnrichmentResponse
from app.services.enrichment_service import EnrichmentService

router = APIRouter()


@router.post(
    "/{file_id}",
    response_model=EnrichmentResponse,
    summary="Enrich extracted document",
    description="Run LLM-based enrichment on the extracted JSON for this file. Optional body: llm_preset, max_concurrent, temperature, max_tokens, top_p.",
)
async def enrich_file(
    file_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: EnrichmentRequestBody | None = None,
):
    """Enrich extraction for the given file_id; persist and return enriched document + sections."""
    files_repo = FilesRepository(db)
    service = EnrichmentService(files_repo)
    opts = body.model_dump(exclude_none=True) if body else {}
    settings = get_settings()
    llm_preset = opts.get("llm_preset") or settings.llm_preset
    result = await service.enrich_file(
        file_id,
        user_id,
        llm_preset=llm_preset,
        max_concurrent=opts.get("max_concurrent"),
        temperature=opts.get("temperature"),
        max_tokens=opts.get("max_tokens"),
        top_p=opts.get("top_p"),
    )
    return EnrichmentResponse(
        document=result["document"],
        sections=result["sections"],
    )
