"""Enrichment service: run LLM-based document/section enrichment and persist result."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import HTTPException, status

from app.extraction.document_analyzer import DocumentSectionAnalyzer
from app.infrastructure.storage import StorageError, get_storage
from app.llm import LLMConfig
from app.repositories.files_repository import FilesRepository


class EnrichmentService:
    """Service for running enrichment on an extracted document and persisting result."""

    def __init__(self, files_repo: FilesRepository) -> None:
        self._repo = files_repo
        self._storage = get_storage()

    async def get_full_extraction(
        self, file_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict[str, Any]:
        """
        Read the full extraction JSON (document + sections) from storage.
        Raises HTTPException on not found or invalid data.
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
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not read extraction: {e}",
            ) from None
        try:
            data = json.loads(content.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid extraction data: {e}",
            ) from None
        if (
            not isinstance(data, dict)
            or "document" not in data
            or "sections" not in data
        ):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid extraction format.",
            ) from None
        return data

    def _save_full_extraction(
        self, relative_path: str, payload: dict[str, Any]
    ) -> None:
        """Persist full extraction JSON to storage."""
        json_bytes = json.dumps(
            payload, indent=2, ensure_ascii=False
        ).encode("utf-8")
        self._storage.save(json_bytes, relative_path)

    async def enrich_file(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        llm_preset: str | None = None,
        max_concurrent: int | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
    ) -> dict[str, Any]:
        """
        Load extraction, run DocumentSectionAnalyzer, overwrite storage with enriched JSON.
        Returns enriched payload with "document" and "sections".
        """
        data = await self.get_full_extraction(file_id, user_id)
        file_record = await self._repo.get_file_by_id(file_id, user_id=user_id)
        if not file_record or not file_record.extracted_doc_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No extraction available.",
            )
        relative_path = file_record.extracted_doc_path

        config = LLMConfig.from_env()
        if temperature is not None:
            config.temperature = temperature
        if max_tokens is not None:
            config.max_tokens = max_tokens
        if top_p is not None:
            config.top_p = top_p

        if llm_preset is None:
            from app.config import get_settings
            llm_preset = get_settings().llm_preset

        analyzer = DocumentSectionAnalyzer(
            preset=llm_preset,
            config=config,
            max_concurrent=max_concurrent ,
        )
        try:
            enriched = await asyncio.to_thread(
                analyzer.process_document,
                data,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg.upper():
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        "LLM rate limit exceeded (429). Reduce load by sending "
                        '"max_concurrent": 2 or 1 in the request body and retry later.'
                    ),
                ) from e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Enrichment failed: {type(e).__name__}: {e}",
            ) from e

        self._save_full_extraction(relative_path, enriched)
        return enriched
