"""
Canonical document and section schemas for the extraction pipeline.
Enrichment fields (document_type, risk_level, audience, state, etc.) are optional.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ExtractionConfidence(str, Enum):
    """Internal-only; not exposed to users. Used for logging and QA."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SectionType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"


class Source(BaseModel):
    """Document source (from file)."""

    file_name: str
    file_hash: str
    upload_date: str  # ISO-8601


class TechnicalContext(BaseModel):
    """Technical context (enrichment layer)."""

    equipment: str | None = None
    version: str | None = None
    workflow: list[str] = Field(default_factory=list)


class DocumentSchema(BaseModel):
    """Logical document. Enrichment fields are optional (overlays)."""

    file_id: uuid.UUID
    source: Source
    document_type: str | None = None
    technical_context: TechnicalContext = Field(default_factory=TechnicalContext)
    risk_level: str | None = None
    audience: list[str] = Field(default_factory=list)
    state: str | None = None
    effective_date: str | None = None
    owner_team: str | None = None
    sections: list[str] = Field(default_factory=list)  # section_id list

    model_config = {"extra": "forbid"}


class SectionSchema(BaseModel):
    """Section = atomic retrieval unit."""

    section_id: str
    file_id: uuid.UUID 
    heading: str
    section_type: SectionType
    content: str
    keywords: list[str] = Field(default_factory=list)

    extraction_confidence: ExtractionConfidence = Field(
        default=ExtractionConfidence.HIGH,
        description="Internal only; used for logging and QA.",
    )

    embedding_vector: list[float] | None = None

    model_config = {"extra": "forbid"}

    def model_dump_public(self, **kwargs: Any) -> dict[str, Any]:
        """Serialize for public API / index; exclude extraction_confidence."""
        data = self.model_dump(**kwargs)
        data.pop("extraction_confidence", None)
        return data


class BlockType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"


class Block(BaseModel):
    """Output of layout extraction (Stage 1)."""

    type: BlockType
    page: int
    bbox: tuple[float, float, float, float] | None = None
    content: str
    caption: str | None = None
    font_size: float | None = None
    is_bold: bool = False


class Segment(BaseModel):
    """Output of structural segmentation (Stage 2)."""

    heading: str
    level: int = 1  # 1-4 (H1-H4)
    section_type: SectionType
    content: str
    page: int = 1
    caption: str | None = None
    extraction_confidence: ExtractionConfidence = ExtractionConfidence.HIGH
