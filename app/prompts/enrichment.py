"""Prompt templates for section and document enrichment."""


def section_enrichment_template(blacklist_preview: str) -> str:
    """Build the prompt for enriching a single section (heading, content, section_summary, keywords)."""
    return f"""You are an assistant that enriches document sections with structured metadata.

Given a section (type and content), respond with a single JSON object (no markdown, no code fence) with exactly these keys:
- "heading": string, clear section title (can refine the existing one).
- "content": string, cleaned or slightly summarized content of the section.
- "section_summary": string, 1-3 sentence summary of the section.
- "keywords": array of strings, relevant terms/concepts from the section (max 15). Do not include generic words. Avoid terms that appear in this blacklist: {blacklist_preview}

Section type: {{section_type}}

Content:
{{content}}

Respond only with the JSON object."""


def document_metadata_template(blacklist_preview: str) -> str:
    """Build the prompt for document-level metadata (document_type, risk_level, audience, etc.)."""
    return f"""You are an assistant that extracts document-level metadata from a technical or regulatory document.

Given the document context below (source, section headings, section keywords), respond with a single JSON object (no markdown, no code fence) with exactly these keys:
- "document_type": string (e.g. SOP, Protocol, Report, Manual).
- "risk_level": string (e.g. Informational, Low, Medium, High, Critical).
- "audience": array of strings (e.g. Operator, QA, Engineer).
- "state": string (e.g. Draft, Approved, Superseded).
- "technical_context": object with optional "equipment", "version", "workflow" (array of strings).
- "effective_date": string or null (ISO date if present).
- "owner_team": string or null.
- "supersedes_file_id": string or null.
- "keywords": array of strings, key terms for the whole document (max 20). Avoid blacklist: {blacklist_preview}
- "keywords_hierarchy": object with optional keys like "core_workflow_terms", "technologies", "biological_materials", "critical_process_steps", "regulatory_or_qc_terms", each an array of strings.

Document context:
{{document_context}}

Respond only with the JSON object."""
