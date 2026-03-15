"""Tests for keyword_polisher: normalization, dedup, blacklist dedup."""

from app.extraction.keyword_polisher import polish_keywords


def test_polish_keywords_normalizes_lowercase():
    """Keywords are lowercased."""
    data = {
        "document": {
            "keywords": [{"term": "Foo Bar", "score": 0.5}],
            "keywords_hierarchy": {
                "core_workflow_terms": [{"term": "Baz", "score": 0.3}]
            },
        },
        "sections": [{"keywords": [{"term": "Section Term", "score": 0.2}]}],
    }
    result = polish_keywords(data)
    assert result["document"]["keywords"][0]["term"] == "foo bar"
    assert (
        result["document"]["keywords_hierarchy"]["core_workflow_terms"][0]["term"]
        == "baz"
    )
    assert result["sections"][0]["keywords"][0]["term"] == "section term"


def test_polish_keywords_dedup():
    """Duplicate keyword strings are removed (first kept)."""
    data = {
        "document": {
            "keywords": [{"term": "dup", "score": 0.5}, {"term": "DUP", "score": 0.3}]
        },
        "sections": [],
    }
    result = polish_keywords(data)
    assert len(result["document"]["keywords"]) == 1
    assert result["document"]["keywords"][0]["term"] == "dup"


def test_polish_keywords_strips_standalone_numbers_in_sections():
    """Section keywords have standalone number tokens removed."""
    data = {
        "document": {},
        "sections": [{"keywords": [{"term": "term 123 value", "score": 0.5}]}],
    }
    result = polish_keywords(data)
    assert result["sections"][0]["keywords"][0]["term"] == "term value"


def test_polish_keywords_preserves_hyphenated_numbers():
    """Hyphenated terms like il-6 are preserved."""
    data = {
        "document": {},
        "sections": [{"keywords": [{"term": "il-6 cytokine", "score": 0.5}]}],
    }
    result = polish_keywords(data)
    assert result["sections"][0]["keywords"][0]["term"] == "il-6 cytokine"


def test_polish_keywords_empty_sections():
    """Empty sections and document are handled."""
    data = {"document": {}, "sections": []}
    result = polish_keywords(data)
    assert result["document"] == {}
    assert result["sections"] == []
