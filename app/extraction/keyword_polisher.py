"""
Keyword polisher for document analyzer output.

Refines and normalizes keywords from the enriched pipeline (document_analyzer):
lowercase normalization, removes standalone numbers from section keywords,
blacklist-based duplicate detection on sections, and deduplicates all keyword lists.

Input/Output: Same structure as document_analyzer (document + sections).
Keywords format: list of {"term": str, "score": float}.

Does NOT modify: keywords_hierarchy structure, scores, or document metadata.

Usage:
  From code (after document_analyzer):
    from app.extraction.keyword_polisher import polish_keywords
    result = polish_keywords({"document": doc, "sections": sections})
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.extraction.keyword_refiner import load_blacklist


def _normalize_kw_string(kw: str) -> str:
    """Lowercase and strip whitespace."""
    return kw.strip().lower()


def _strip_standalone_numbers(kw: str) -> str:
    """Remove tokens that are purely digits. Preserves hyphenated terms like 'il-6'."""
    tokens = kw.split()
    filtered = [t for t in tokens if not re.fullmatch(r"\d+", t)]
    return " ".join(filtered).strip()


def _reduced_token_set(kw: str, blacklist: set[str]) -> frozenset[str]:
    """Tokenize keyword and remove blacklist words; return frozen set of remaining tokens."""
    tokens = kw.lower().split()
    return frozenset(t for t in tokens if t not in blacklist)


# ── Convert between Atlas format and list format ───────────────────────────

def _to_pair(item: dict[str, Any] | list | tuple) -> list:
    """Normalize to [term, score] from {"term", "score"} or [term, score]."""
    if isinstance(item, dict) and "term" in item:
        return [str(item["term"]), float(item.get("score", 0.0))]
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        return [str(item[0]), float(item[1])]
    if isinstance(item, (list, tuple)) and len(item) >= 1:
        return [str(item[0]), 0.0]
    return [str(item), 0.0]


def _to_object(pair: list) -> dict[str, Any]:
    """Convert [term, score] to {"term": str, "score": float}."""
    return {"term": str(pair[0]), "score": float(pair[1])}


# ── Tuple/list helpers ─────────────────────────────────────────────────────

def _normalize_kw_pair(pair: list, strip_numbers: bool = False) -> list:
    """Normalize keyword string inside a [keyword, score] pair."""
    kw = _normalize_kw_string(str(pair[0]))
    if strip_numbers:
        kw = _strip_standalone_numbers(kw)
    return [kw, pair[1]] if len(pair) >= 2 else [kw]


def _dedup_kw_list(kw_list: list[list]) -> list[list]:
    """Remove exact-duplicate keyword strings, keeping first occurrence."""
    seen: set[str] = set()
    out: list[list] = []
    for pair in kw_list:
        k = pair[0]
        if k and k not in seen:
            seen.add(k)
            out.append(pair)
    return out


# ── Blacklist duplicate detection (sections only) ───────────────────────────

def _blacklist_dedup_section(kw_list: list[list], blacklist: set[str]) -> list[list]:
    """
    If two keywords differ only by the presence of blacklist words,
    keep the shorter (cleaner) version.
    """
    groups: dict[frozenset[str], list[int]] = {}
    for idx, pair in enumerate(kw_list):
        reduced = _reduced_token_set(pair[0], blacklist)
        if not reduced:
            continue
        groups.setdefault(reduced, []).append(idx)

    remove_indices: set[int] = set()
    for indices in groups.values():
        if len(indices) <= 1:
            continue
        shortest_idx = min(indices, key=lambda i: len(kw_list[i][0]))
        for i in indices:
            if i != shortest_idx:
                remove_indices.add(i)

    return [pair for idx, pair in enumerate(kw_list) if idx not in remove_indices]


# ── Main polishing logic ───────────────────────────────────────────────────

def _polish_document_keywords(doc: dict[str, Any]) -> dict[str, Any]:
    """Normalize document-level keywords and keywords_hierarchy (no number stripping)."""
    doc = dict(doc)

    if "keywords" in doc and isinstance(doc["keywords"], list):
        pairs = [_to_pair(p) for p in doc["keywords"] if p]
        pairs = [_normalize_kw_pair(p) for p in pairs]
        doc["keywords"] = [_to_object(p) for p in _dedup_kw_list(pairs)]

    if "keywords_hierarchy" in doc and isinstance(doc["keywords_hierarchy"], dict):
        hierarchy = {}
        for cat, kw_list in doc["keywords_hierarchy"].items():
            if not isinstance(kw_list, list):
                hierarchy[cat] = kw_list
                continue
            pairs = [_to_pair(p) for p in kw_list if p]
            normalized = [_normalize_kw_pair(p) for p in pairs]
            hierarchy[cat] = [_to_object(p) for p in _dedup_kw_list(normalized)]
        doc["keywords_hierarchy"] = hierarchy

    return doc


def _polish_section_keywords(
    section: dict[str, Any],
    blacklist: set[str],
) -> dict[str, Any]:
    """Normalize section keywords: lowercase, strip numbers, blacklist dedup, dedup."""
    section = dict(section)

    if "keywords" not in section or not isinstance(section["keywords"], list):
        return section

    pairs = [_to_pair(p) for p in section["keywords"] if p]
    normalized = [_normalize_kw_pair(p, strip_numbers=True) for p in pairs]
    normalized = [p for p in normalized if p[0]]
    cleaned = _blacklist_dedup_section(normalized, blacklist)
    section["keywords"] = [_to_object(p) for p in _dedup_kw_list(cleaned)]
    return section


def polish_keywords(
    data: dict[str, Any],
    *,
    blacklist: set[str] | None = None,
) -> dict[str, Any]:
    """
    Polish enriched pipeline output (document + sections).

    Normalizes keywords (lowercase), strips standalone numbers from section
    keywords, applies blacklist-based dedup to sections, and deduplicates
    all keyword lists. Preserves structure and scores.

    Args:
        data: Dict with "document" and "sections" (same as document_analyzer output).
        blacklist: Optional set of stop words; uses load_blacklist() if None.

    Returns:
        New dict with polished document and sections (Atlas format: {"term", "score"}).
    """
    data = dict(data)
    blacklist = blacklist if blacklist is not None else load_blacklist()

    if "document" in data and isinstance(data["document"], dict):
        data["document"] = _polish_document_keywords(data["document"])

    if "sections" in data and isinstance(data["sections"], list):
        data["sections"] = [
            _polish_section_keywords(s, blacklist) for s in data["sections"]
        ]

    return data
