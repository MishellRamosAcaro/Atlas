"""
Extraction pipeline: bytes + content_type -> Document + Sections.
Reusable for PDF (now) and DOC/TXT (future).
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import datetime, timezone

from app.extraction.block_cleaner import clean_blocks

from app.extraction.keywords import extract_keywords_for_sections
from app.extraction.layout_extraction import extract_layout_from_bytes
from app.extraction.schemas import (
    DocumentSchema,
    SectionSchema,
    Source,
)
from app.extraction.semantic_chunking import chunk_to_sections
from app.extraction.structural_segmentation import segment_document

logger = logging.getLogger(__name__)

# PDF MIME and extension
PDF_CONTENT_TYPES = {"application/pdf"}
PDF_EXTENSIONS = {".pdf"}


def extract_document(
    content: bytes,
    file_name: str,
    content_type: str,
    *,
    file_id: uuid.UUID,
    apply_block_cleaning: bool = False,
    include_keywords: bool = True,
) -> tuple[DocumentSchema, list[SectionSchema]]:
 
    if not _is_pdf(content_type, file_name):
        raise ValueError(
            f"Unsupported type for extraction: {content_type} / {file_name}"
        )

    file_hash = hashlib.sha256(content).hexdigest()
    upload_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    source = Source(
        file_name=file_name,
        file_hash=file_hash,
        upload_date=upload_date,
    )

    blocks = extract_layout_from_bytes(content, use_pypdf=True)
    logger.info("Layout extraction: %d blocks from %s", len(blocks), file_name)

    if apply_block_cleaning:
        blocks = clean_blocks(blocks)
        logger.info("Block cleaning: %d blocks after filter", len(blocks))

    segments = segment_document(blocks)
    logger.info("Structural segmentation: %d segments", len(segments))

    document, sections = chunk_to_sections(
        segments, file_id=file_id, source=source
    )
    logger.info("Semantic chunking: %d sections", len(sections))

    sections = [
        s.model_copy(update={"content": _normalize_content(s.content)})
        for s in sections
    ]

    if include_keywords:
        sections = extract_keywords_for_sections(sections)

    return document, sections


def _normalize_content(text: str) -> str:
    """Replace newlines and collapse any run of whitespace to a single space."""
    if not text:
        return text
    return re.sub(r"\s+", " ", text).strip()


def _is_pdf(content_type: str, file_name: str) -> bool:
    """Return True if content is PDF by type or extension."""
    base_type = (content_type or "").split(";")[0].strip().lower()
    if base_type in PDF_CONTENT_TYPES:
        return True
    ext = (
        "." + (file_name or "").rsplit(".", 1)[-1].lower()
        if "." in (file_name or "")
        else ""
    )
    return ext in PDF_EXTENSIONS
