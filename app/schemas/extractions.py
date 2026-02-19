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


class ExtractedDocumentFields(BaseModel):
    """Selected fields from the extracted document (GET /extractions/{file_id}/document)."""

    file_id: str | None = Field(None, description="File identifier (UUID as string).")
    source: str | dict | None = Field(
        None,
        description="Document source (filename string or object with file_name, file_hash, upload_date).",
    )
    document_type: str | None = Field(None, description="Type of document.")
    technical_context: dict | None = Field(
        None,
        description="Technical context (equipment, version, workflow).",
    )
    risk_level: str | None = Field(None, description="Risk level.")
    audience: list[str] = Field(
        default_factory=list,
        description="Target audience.",
    )
    state: str | None = Field(None, description="Document state.")
    effective_date: str | None = Field(None, description="Effective date.")
    owner_team: str | None = Field(None, description="Owner team.")


class ExtractedDocumentResponse(BaseModel):
    """Response for GET /extractions/{file_id}/document: document with selected fields."""

    document: ExtractedDocumentFields = Field(
        ...,
        description="Document fields (file_id, source, document_type, technical_context, risk_level, audience, state, effective_date, owner_team).",
    )
