"""Unit tests for keyword_refiner: blacklist, section and document refiner."""

import pytest

from app.extraction.keyword_refiner import (
    keyword_refiner_document,
    keyword_refiner_section,
    load_blacklist,
)


def test_load_blacklist_returns_global_blacklist():
    """load_blacklist() returns global BLACKLIST as set."""
    result = load_blacklist()
    assert isinstance(result, set)
    assert "the" in result
    assert "a" in result


def test_keyword_refiner_section_filters_blacklist():
    """keyword_refiner_section excludes blacklisted terms."""
    blacklist = {"generic", "the"}
    raw = ["term1", "generic", "term2", "the", "term3"]
    result = keyword_refiner_section(
        "content",
        "heading",
        raw,
        blacklist=blacklist,
        top_k=20,
    )
    terms = [t[0] for t in result]
    assert "term1" in terms
    assert "term2" in terms
    assert "term3" in terms
    assert "generic" not in terms
    assert "the" not in terms


def test_keyword_refiner_section_respects_top_k():
    """keyword_refiner_section returns at most top_k items."""
    raw = [f"kw{i}" for i in range(20)]
    result = keyword_refiner_section(
        "content",
        "heading",
        raw,
        blacklist=set(),
        top_k=5,
    )
    assert len(result) <= 5


def test_keyword_refiner_document_with_hierarchy():
    """keyword_refiner_document builds keywords from hierarchy dict (scored per category)."""
    section_kw = [[("a", 1.0), ("b", 1.0)]]
    doc_raw = {
        "core_workflow_terms": ["x", "y"],
        "technologies": ["z"],
    }
    result = keyword_refiner_document(
        section_keywords_per_section=section_kw,
        document_raw_keywords_or_hierarchy=doc_raw,
        document_context={},
        blacklist=set(),
        top_per_category=15,
    )
    assert "keywords_hierarchy" in result
    hierarchy = result["keywords_hierarchy"]
    assert "core_workflow_terms" in hierarchy
    assert "technologies" in hierarchy
    # Each category is list of (term, score) tuples
    core_terms = [t[0] for t in hierarchy["core_workflow_terms"]]
    assert "x" in core_terms and "y" in core_terms
    tech_terms = [t[0] for t in hierarchy["technologies"]]
    assert "z" in tech_terms
    assert "keywords" in result
    assert isinstance(result["keywords"], list)


def test_keyword_refiner_document_with_list():
    """keyword_refiner_document accepts raw list of keywords."""
    section_kw = []
    doc_raw = ["doc1", "doc2"]
    result = keyword_refiner_document(
        section_keywords_per_section=section_kw,
        document_raw_keywords_or_hierarchy=doc_raw,
        document_context={},
        blacklist=set(),
        top_per_category=15,
    )
    assert "keywords" in result
    terms = [t[0] for t in result["keywords"]]
    assert "doc1" in terms or "doc2" in terms
