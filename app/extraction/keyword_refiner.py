"""Keyword refiner: blacklist filter and scoring for section/document keywords."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_blacklist(path: Path | str | None = None) -> set[str]:
    """Load blacklist of terms to exclude from keywords. Returns empty set if file missing."""
    if path is None:
        return set()
    p = Path(path)
    if not p.is_file():
        return set()
    try:
        text = p.read_text(encoding="utf-8")
        return {line.strip().lower() for line in text.splitlines() if line.strip()}
    except Exception:
        return set()


def _normalize(t: str) -> str:
    return t.strip().lower()


def _filter_blacklist(candidates: list[str], blacklist: set[str]) -> list[str]:
    return [c for c in candidates if _normalize(c) not in blacklist and len(c.strip()) > 1]


def keyword_refiner_section(
    content: str,
    heading: str,
    raw_keywords: list[str],
    *,
    blacklist: set[str] | None = None,
    top_k: int = 15,
) -> list[tuple[str, float]]:
    """Filter and score section keywords; return list of (term, score)."""
    blacklist = blacklist or set()
    filtered = _filter_blacklist([str(k).strip() for k in raw_keywords if k], blacklist)
    # Simple scoring: 1.0 for each; could later use position/frequency.
    scored = [(t, 1.0) for t in filtered[:top_k]]
    return scored


def keyword_refiner_document(
    section_keywords_per_section: list[list[tuple[str, float]] | list[Any]],
    document_raw_keywords_or_hierarchy: dict[str, list[str]] | list[str] | list[Any],
    document_context: dict[str, Any],
    *,
    blacklist: set[str] | None = None,
    top_per_category: int = 15,
) -> dict[str, Any]:
    """Build document-level keywords and keywords_hierarchy from section keywords and LLM raw output."""
    blacklist = blacklist or set()
    flat: list[str] = []
    for kw in section_keywords_per_section:
        if isinstance(kw, list):
            for item in kw:
                if isinstance(item, dict) and "term" in item:
                    flat.append(str(item["term"]).strip())
                elif isinstance(item, (list, tuple)) and len(item) >= 1:
                    flat.append(str(item[0]).strip())
                elif isinstance(item, str):
                    flat.append(item.strip())
        else:
            continue
    raw = document_raw_keywords_or_hierarchy
    if isinstance(raw, dict):
        hierarchy = {k: v for k, v in raw.items() if isinstance(v, list)}
        doc_keywords = []
        for v in hierarchy.values():
            doc_keywords.extend([str(x).strip() for x in v if x])
    elif isinstance(raw, list):
        hierarchy = {}
        doc_keywords = [str(x).strip() for x in raw if x]
    else:
        hierarchy = {}
        doc_keywords = []
    combined = _filter_blacklist(list(dict.fromkeys(flat + doc_keywords)), blacklist)
    keywords = [(t, 1.0) for t in combined[:top_per_category * 2]]
    return {
        "keywords_hierarchy": hierarchy,
        "keywords": keywords,
    }
