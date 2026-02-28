"""Request/response schemas for enrichments API."""

from typing import Literal

from pydantic import BaseModel, Field

LLM_PRESET_CHOICES = Literal[
    "claude-haiku",
    "gemini-flash",
    "deepseek_reasoner",
    "deepseek_chat",
    "openai-chatgpt",
]


class EnrichmentRequestBody(BaseModel):
    """Optional body for POST /enrichments/{file_id}. All fields optional."""

    llm_preset: LLM_PRESET_CHOICES | None = Field(
        None,
        description="LLM preset: claude-haiku, gemini-flash, deepseek_reasoner, deepseek_chat, openai-chatgpt.",
    )
    max_concurrent: int | None = Field(
        None,
        description="Max concurrent section LLM calls.",
    )
    temperature: float | None = Field(
        None,
        description="LLM temperature.",
    )
    max_tokens: int | None = Field(
        None,
        description="LLM max output tokens.",
    )
    top_p: float | None = Field(
        None,
        description="LLM top_p.",
    )


class EnrichmentResponse(BaseModel):
    """Response for POST /enrichments/{file_id}: enriched document and sections."""

    document: dict = Field(
        ...,
        description="Enriched document (metadata, keywords_hierarchy, keywords).",
    )
    sections: list[dict] = Field(
        default_factory=list,
        description="Enriched sections (heading, content, section_summary, keywords with scores).",
    )
