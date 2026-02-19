"""Extractions endpoint: run extraction on an uploaded file."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user_id
from app.repositories.files_repository import FilesRepository
from app.schemas.extractions import (
    ExtractedDocumentFields,
    ExtractionResponse,
    ExtractedDocumentResponse,
)
from app.services.extraction_service import ExtractionService

router = APIRouter()


@router.get(
    "/{file_id}/document",
    response_model=ExtractedDocumentResponse,
    summary="Get extracted document",
    description="Return the document section of the extracted JSON for this file (from extracted_doc_path). Only the file owner can access. Returns 404 if file has no extraction.",
)
async def get_extracted_document(
    file_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Read extracted JSON from storage and return document section."""
    files_repo = FilesRepository(db)
    service = ExtractionService(files_repo)
    document = await service.get_extracted_document(file_id, user_id)
    fields = ExtractedDocumentFields(
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
    return ExtractedDocumentResponse(document=fields)


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
