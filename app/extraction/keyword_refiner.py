"""
Term frequency and refinement for section and document keywords.

- keyword_refiner_section: TF_local, appears_in_heading, is_technical_term -> score; ranking.
- keyword_refiner_document: TF_global, num_sections_present, appears_in_title_or_intended_use -> score; hierarchical output.

Uses lowercase normalization, n-gram detection (2-3), blacklist filtering.
"""

from __future__ import annotations

import re
from typing import Any

from app.prompts.enrichment_global_variables import BLACKLIST, HIERARCHY_KEYS




def load_blacklist() -> set[str]:
    """Return global BLACKLIST as set."""
    return set[str](BLACKLIST)


def _normalize_lower(text: str) -> str:
    return text.strip().lower()


def _tokenize(text: str) -> list[str]:
    """Simple tokenization: letters, digits, hyphens; split on non-alphanumeric."""
    text = _normalize_lower(text)
    return [t for t in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text) if t]


def _extract_ngrams(tokens: list[str], n: int) -> list[str]:
    """Extract n-grams from token list."""
    if len(tokens) < n:
        return []
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def _term_in_text(term: str, text_lower: str) -> int:
    """Count occurrences of term (as whole word) in text. Case-insensitive."""
    pattern = r"\b" + re.escape(term.lower()) + r"\b"
    return len(re.findall(pattern, text_lower))


def keyword_refiner_section(
    content: str,
    heading: str,
    raw_keywords: list[str],
    *,
    blacklist: set[str] | None = None,
    top_k: int = 15,
) -> list[tuple[str, float]]:
    """
    Refine section keywords: blacklist filter, 2-3 n-grams from content that overlap raw,
    score = TF_local * 0.6 + appears_in_heading * 0.3 + is_technical_term * 0.1.

    Returns top_k (keyword, score) tuples with score rounded to 3 decimals.
    """
    blacklist = blacklist or set()
    content_lower = _normalize_lower(content)
    heading_lower = _normalize_lower(heading)
    tokens = _tokenize(content)

    # Build candidate set: raw keywords (filtered) + 2–3 grams from content that overlap raw
    candidates: list[str] = []
    seen_normalized: set[str] = set()
    for kw in raw_keywords:
        k = _normalize_lower(kw.strip())
        if not k or k in blacklist or len(k) <= 1:
            continue
        if k in seen_normalized:
            continue
        seen_normalized.add(k)
        candidates.append(kw.strip())

    # Add 2–3 grams from content that appear in raw or overlap
    for n in (2, 3):
        for ng in _extract_ngrams(tokens, n):
            if ng in blacklist or ng in seen_normalized:
                continue
            for c in candidates:
                if ng in _normalize_lower(c) or _normalize_lower(c) in ng:
                    seen_normalized.add(ng)
                    candidates.append(ng)
                    break

    if not candidates:
        return []

    # TF_local: count in section content (normalize to 0–1 by max count)
    counts = [(c, _term_in_text(c, content_lower)) for c in candidates]
    max_count = max((x[1] for x in counts), default=1)
    if max_count == 0:
        max_count = 1
    tf_local = {c: (cnt / max_count) for c, cnt in counts}

    # appears_in_heading: 0 or 1; is_technical_term: 0.1 constant
    scores: list[tuple[str, float]] = []
    for c in candidates:
        tf = tf_local.get(c, 0.0)
        in_heading = 1.0 if _term_in_text(c, heading_lower) > 0 else 0.0
        technical = 0.1
        score = (tf * 0.6) + (in_heading * 0.3) + (technical * 0.1)
        scores.append((c, score))

    scores.sort(key=lambda x: -x[1])
    return [(s[0], round(s[1], 3)) for s in scores[:top_k]]


def _section_kw_to_str(item: str | tuple[str, float] | list | dict[str, Any]) -> str | None:
    """Normalize section keyword item to string (for document refiner input)."""
    if isinstance(item, dict) and "term" in item:
        return str(item["term"]).strip() or None
    if isinstance(item, (list, tuple)) and len(item) >= 1:
        return str(item[0]).strip() or None
    if isinstance(item, str):
        return item.strip() or None
    return None


def keyword_refiner_document(
    section_keywords_per_section: list[list[tuple[str, float]] | list[Any]],
    document_raw_keywords_or_hierarchy: dict[str, list[str]] | list[str] | list[Any],
    document_context: dict[str, Any],
    *,
    blacklist: set[str] | None = None,
    top_per_category: int = 15,
) -> dict[str, Any]:
    """
    Refine document-level keywords. Input can be flat list or keywords_hierarchy dict.
    section_keywords_per_section can be list of list of str, (keyword, score) tuples, or dict with "term"/"score".
    Score: (TF_global * 0.5) + (num_sections_present * 0.3) + (appears_in_title_or_intended_use * 0.2).
    Returns dict with "keywords_hierarchy" (per HIERARCHY_KEYS) and "keywords" as list of (term, score).
    """
    blacklist = blacklist or set()

    title = _normalize_lower(document_context.get("title") or "")
    intended = _normalize_lower(document_context.get("intended_use") or "")
    first_headings = document_context.get("first_headings") or []
    title_use_text = title + " " + intended + " " + " ".join(_normalize_lower(h) for h in first_headings)

    def appears_in_title_or_intended_use(term: str) -> float:
        return 1.0 if _term_in_text(_normalize_lower(term), title_use_text) > 0 else 0.0

    # Flatten section keywords and collect per-term stats (support dict, tuple, str)
    all_terms_flat: list[str] = []
    term_sections: dict[str, set[int]] = {}
    for i, kw_list in enumerate(section_keywords_per_section):
        if not isinstance(kw_list, list):
            continue
        for kw in kw_list:
            t = _section_kw_to_str(kw)
            if t is None:
                continue
            k = _normalize_lower(t)
            if not k or k in blacklist or len(k) <= 1:
                continue
            all_terms_flat.append(t)
            term_sections.setdefault(k, set()).add(i)

    num_sections = len(section_keywords_per_section) or 1
    tf_global_counts: dict[str, int] = {}
    for t in all_terms_flat:
        k = _normalize_lower(t)
        tf_global_counts[k] = tf_global_counts.get(k, 0) + 1
    max_tf = max(tf_global_counts.values(), default=1)
    if max_tf == 0:
        max_tf = 1

    raw = document_raw_keywords_or_hierarchy

    if isinstance(raw, dict):
        # Input is hierarchy: score per category
        result_hierarchy: dict[str, list[tuple[str, float]]] = {k: [] for k in HIERARCHY_KEYS}
        for cat in HIERARCHY_KEYS:
            terms = raw.get(cat)
            if not isinstance(terms, list):
                continue
            scored = []
            for t in terms:
                t_clean = t.strip() if isinstance(t, str) else str(t).strip()
                k = _normalize_lower(t_clean)
                if not k or k in blacklist:
                    continue
                tf_g = tf_global_counts.get(k, 0) / max_tf
                n_sec = len(term_sections.get(k, set())) / num_sections
                in_title = appears_in_title_or_intended_use(t_clean)
                score = (tf_g * 0.5) + (n_sec * 0.3) + (in_title * 0.2)
                scored.append((t_clean, score))
            scored.sort(key=lambda x: -x[1])
            result_hierarchy[cat] = [(s[0], round(s[1], 3)) for s in scored[:top_per_category]]
        flat: list[tuple[str, float]] = []
        for v in result_hierarchy.values():
            flat.extend(v)
        return {"keywords_hierarchy": result_hierarchy, "keywords": flat}
    else:
        # Input is flat list (e.g. from LLM)
        terms = raw if isinstance(raw, list) else []
        scored = []
        seen: set[str] = set()
        for t in terms:
            t_clean = t.strip() if isinstance(t, str) else str(t).strip()
            k = _normalize_lower(t_clean)
            if not k or k in blacklist or k in seen:
                continue
            seen.add(k)
            tf_g = tf_global_counts.get(k, 0) / max_tf
            n_sec = len(term_sections.get(k, set())) / num_sections
            in_title = appears_in_title_or_intended_use(t_clean)
            score = (tf_g * 0.5) + (n_sec * 0.3) + (in_title * 0.2)
            scored.append((t_clean, score))
        scored.sort(key=lambda x: -x[1])
        top_flat: list[tuple[str, float]] = [(s[0], round(s[1], 3)) for s in scored[: top_per_category * 2]]
        result_hierarchy = {k: [] for k in HIERARCHY_KEYS}
        result_hierarchy["core_workflow_terms"] = top_flat[:top_per_category]
        return {"keywords_hierarchy": result_hierarchy, "keywords": top_flat}
