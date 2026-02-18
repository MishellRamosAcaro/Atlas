"""Request/response schemas for extractions API."""

from pydantic import BaseModel, Field


class ExtractionResponse(BaseModel):
    """Response for POST /extractions/{file_id}: document + sections (JSON only)."""

    document: dict = Field(
        ..., description="Document object (file_id, source, sections list, etc.)"
    )
    sections: list[dict] = Field(
        default_factory=list,
        description="List of section objects (section_id, file_id, heading, section_type, content, keywords)",
    )
