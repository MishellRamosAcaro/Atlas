"""Extraction service: read file from storage, run pipeline, persist JSON, update DB."""

import asyncio
import json
import uuid
from pathlib import Path

from fastapi import HTTPException, status

from app.extraction.pipeline import extract_document
from app.infrastructure.storage import StorageError, get_storage
from app.models.file import FILE_STATUS_CLEAN
from app.repositories.files_repository import FilesRepository

PDF_EXTENSIONS = {".pdf"}
PDF_CONTENT_TYPES = {"application/pdf"}


def _is_pdf(content_type: str, filename: str) -> bool:
    """Return True if file is PDF by content_type or extension."""
    base_type = (content_type or "").split(";")[0].strip().lower()
    if base_type in PDF_CONTENT_TYPES:
        return True
    ext = Path(filename or "").suffix.lower()
    return ext in PDF_EXTENSIONS


class ExtractionService:
    """Service for running extraction on an uploaded file and persisting result."""

    def __init__(
        self,
        files_repo: FilesRepository,
    ) -> None:
        self._repo = files_repo
        self._storage = get_storage()

    async def extract_from_file(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict:
        """
        Run extraction on the file, save JSON to storage, update extracted_doc_path.
        Returns JSON-serializable dict with document and sections (public, no extraction_confidence).
        """
        file_record = await self._repo.get_file_by_id(file_id, user_id=user_id)
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found.",
            )
        if file_record.status != FILE_STATUS_CLEAN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not available for extraction (must be CLEAN).",
            )
        if not _is_pdf(file_record.content_type or "", file_record.filename or ""):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files can be extracted.",
            )

        try:
            stream = self._storage.open(file_record.stored_path)
            content = stream.read()
            stream.close()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File content could not be read.",
            ) from e

        try:
            if file_record.filename is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File name is required.",
                )
            if file_record.content_type is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Content type is required."
                )
            document, sections = await asyncio.to_thread(
                extract_document,
                content,
                file_record.filename,
                file_record.content_type,
                file_id=file_id,
                include_keywords=True,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Extraction failed.",
            ) from e

        section_dumps = [s.model_dump_public(mode="json") for s in sections]
        payload = {
            "document": document.model_dump(mode="json"),
            "sections": section_dumps,
        }
        json_bytes = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")

        relative_path = f"staging/{user_id}/extractions/{file_id}.json"
        self._storage.save(json_bytes, relative_path)

        await self._repo.update_extracted_doc_path(file_id, user_id, relative_path)

        return payload

    async def get_extracted_document(
        self, file_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict:
        """
        Read the extracted JSON from storage and return the document section.

        Returns the "document" key from staging/{user_id}/extractions/{file_id}.json.
        Raises HTTPException 404 if file not found, not owned, or no extraction;
        404/500 if storage read or JSON parse fails.
        """
        file_record = await self._repo.get_file_by_id(file_id, user_id=user_id)
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found.",
            )
        if not file_record.extracted_doc_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No extraction available for this file.",
            )
        try:
            stream = self._storage.open(file_record.extracted_doc_path)
            content = stream.read()
            stream.close()
        except StorageError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Extraction file not found.",
            ) from None
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not read extraction.",
            ) from None
        try:
            data = json.loads(content.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid extraction data.",
            ) from None
        if not isinstance(data, dict) or "document" not in data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid extraction format.",
            ) from None
        return data["document"]
