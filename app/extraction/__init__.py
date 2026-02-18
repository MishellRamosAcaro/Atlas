"""PDF/document extraction pipeline. Entry point: extract_document(content, file_name, content_type)."""

from app.extraction.pipeline import extract_document
from app.extraction.schemas import (
    DocumentSchema,
    SectionSchema,
    Source,
)

__all__ = [
    "extract_document",
    "DocumentSchema",
    "SectionSchema",
    "Source",
]
