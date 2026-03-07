"""Prompt templates for section and document enrichment."""

from app.prompts.enrichment_global_variables import BLACKLIST, DOCUMENT_TYPE_VALUES, RISK_LEVEL_VALUES, AUDIENCE_VALUES, STATE_VALUES


def section_enrichment_template() -> str:
    """Build the prompt for enriching a single section (heading, content, section_summary, keywords)."""
    return f"""You are an FAS expert in document intelligence. Your task is to enrich ONE section from a pipeline-extracted document. The document uses SECTIONS as atomic units (not chunks).

STRICT RULES:
- Do NOT change or output section_id, doc_id. They are immutable.
- Output ONLY a single JSON object with these keys: "heading", "content", "section_summary", "keywords".
- heading: If the section's heading is empty or missing, infer a short title from the content. Otherwise keep or slightly normalize the existing heading.
- content: Restructure and normalize the content (clear paragraphs, bullet points, numbered steps where appropriate, list, spacing) without changing the meaning. Preserve technical details and nuance; improve formatting and clarity. Do not drop information. If section_type is "figure" or "table", keep ONLY the caption description (one short paragraph); do not keep raw table cells or figure data.
- section_summary: A summary of the section in 1-2 sentences, including the meaning of the section.
- keywords: List of the most relevant BIOLOGICAL and technical keywords for this section.
  * Apply MINIMUM FREQUENCY: prefer terms that appear at least 2 times in the section and/or represent essential protocol steps.
  * Restrict to BIOMEDICAL/TECHNICAL vocabulary. Prioritize biology-related terms (genes, assays, equipment, organisms, named procedures).
  * Do NOT use these generic terms (blacklist): """ + ", ".join(BLACKLIST) + """
  * Differentiate CENTRAL THEME (main workflow, critical steps) from merely mentioned terms; prefer central terms, exclude generic terms and terms not central to the workflow.
  * 3-15 keywords per section.

Output format (valid JSON only, no markdown):
{{"heading": "...", "content": "...", "section_summary": "...", "keywords": ["kw1", "kw2", ...]}}

SECTION (section_type and content only; IDs must not be changed):
section_type: {section_type}
content:
{content}
"""





def document_metadata_template() -> str:
    """Build the prompt for document-level metadata (document_type, risk_level, audience, etc.)."""
    return f"""You are an FAS expert in document intelligence. Given the full document context (source, section headings, and section keywords), fill the document-level metadata AND document-level keywords in hierarchical form.

ALLOWED VALUES (use exactly these):
- document_type: one of """ + DOCUMENT_TYPE_VALUES + """
- risk_level: one of """ + RISK_LEVEL_VALUES + """
- audience: list of one or more of """ + AUDIENCE_VALUES + """
- state: one of """ + STATE_VALUES + """
- technical_context: object with "equipment" (string or null), "version" (string or null), "workflow" (list of strings, e.g. ["NGS", "ELISA"])
- effective_date: ISO-8601 date string or null
- owner_team: string or null (e.g. QA, R&D, Applications)
- supersedes_doc_id: string or null
- keywords: list of most important terms (biological and technical).
- keywords_hierarchy: object with exactly these keys, each a list of strings:
  - core_workflow_terms
  - technologies
  - biological_materials
  - critical_process_steps
  - regulatory_or_qc_terms
  Use biomedical vocabulary; avoid blacklist: """ + ", ".join(BLACKLIST) + """
  Include terms that appear in multiple sections or in title/intended use; exclude generic terms.

Document context:
{document_context}

Respond with a single JSON object with keys: document_type, risk_level, audience, state, technical_context, effective_date, owner_team, supersedes_doc_id, keywords, keywords_hierarchy.
"""
