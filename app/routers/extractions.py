"""Extractions endpoint: run extraction on an uploaded file."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user_id
from app.repositories.files_repository import FilesRepository
from app.schemas.extractions import ExtractionResponse
from app.services.extraction_service import ExtractionService

router = APIRouter()


@router.post(
    "/{file_id}",
    response_model=ExtractionResponse,
    summary="Extract document from file",
    description="Run extraction on an uploaded PDF (file must be CLEAN). Returns document + sections as JSON and persists the result in storage. Updates the file's extracted_doc_path reference.",
)
async def extract_file(
    file_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Run extraction pipeline on the file; persist JSON; return document + sections."""
    files_repo = FilesRepository(db)
    service = ExtractionService(files_repo)
    payload = await service.extract_from_file(file_id, user_id)
    return ExtractionResponse(**payload)
