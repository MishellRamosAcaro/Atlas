"""
Keyword extraction for sections (headings, bold, table headers).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.extraction.schemas import SectionSchema, SectionType

if TYPE_CHECKING:
    pass  # Block from layout_extraction if needed


def extract_keywords_from_section(
    section: SectionSchema,
    *,
    bold_phrases: list[str] | None = None,
    table_header_row: str | None = None,
) -> list[str]:
    """Extract keywords for a section from heading and optionally bold/table header."""
    keywords: list[str] = []
    seen: set[str] = set()

    def add(*candidates: str):
        for c in candidates:
            c = _normalize(c)
            if c and c not in seen and len(c) > 1:
                seen.add(c)
                keywords.append(c)

    if section.heading and section.heading.strip():
        for word in _tokenize_heading(section.heading):
            add(word)

    if section.section_type == SectionType.TABLE and table_header_row:
        for cell in re.split(r"\s*\|\s*", table_header_row):
            add(cell.strip())

    if bold_phrases:
        for phrase in bold_phrases:
            for word in _tokenize_heading(phrase):
                add(word)

    return keywords[:50]


def extract_keywords_for_sections(
    sections: list[SectionSchema],
    *,
    section_bold_phrases: dict[str, list[str]] | None = None,
    section_table_headers: dict[str, str] | None = None,
) -> list[SectionSchema]:
    """Add keywords to each section. Returns new section list with keywords populated."""
    section_bold_phrases = section_bold_phrases or {}
    section_table_headers = section_table_headers or {}
    result = []
    for sec in sections:
        kw = extract_keywords_from_section(
            sec,
            bold_phrases=section_bold_phrases.get(sec.section_id),
            table_header_row=section_table_headers.get(sec.section_id),
        )
        result.append(sec.model_copy(update={"keywords": kw}))
    return result


def _normalize(s: str) -> str:
    s = s.strip()
    if not s:
        return ""
    s = s[:80]
    return s


def _tokenize_heading(heading: str) -> list[str]:
    """Split heading into candidate words/phrases."""
    heading = heading.strip()
    if not heading:
        return []
    tokens = re.findall(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", heading)
    return [t for t in tokens if len(t) >= 2 or t.isdigit()]
