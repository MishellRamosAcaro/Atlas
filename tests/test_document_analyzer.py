"""Unit tests for document_analyzer: parse JSON from response, IDs unchanged."""

import json
from unittest.mock import MagicMock, patch


from app.extraction.document_analyzer import (
    DocumentSectionAnalyzer,
    _parse_json_from_response,
)


def test_parse_json_from_response_raw():
    """Parse valid raw JSON."""
    data = {"heading": "Foo", "content": "Bar", "keywords": []}
    assert _parse_json_from_response(json.dumps(data)) == data


def test_parse_json_from_response_fenced_block():
    """Parse JSON inside ```json ... ``` block."""
    data = {"a": 1, "b": "two"}
    text = "Some text\n```json\n" + json.dumps(data) + "\n```\nmore"
    assert _parse_json_from_response(text) == data


def test_parse_json_from_response_fenced_block_no_lang():
    """Parse JSON inside ``` ... ``` (no json label)."""
    data = {"x": 42}
    text = "```\n" + json.dumps(data) + "\n```"
    assert _parse_json_from_response(text) == data


def test_parse_json_from_response_returns_none_on_invalid():
    """Return None when no valid JSON found."""
    assert _parse_json_from_response("not json at all") is None
    assert _parse_json_from_response("") is None


@patch("app.extraction.document_analyzer.BLACKLIST", [])
def test_process_document_does_not_modify_section_id_or_file_id():
    """Enrichment must not change section_id or file_id."""
    import uuid

    file_id = uuid.uuid4()
    section_id = "sec-001"
    input_json = {
        "document": {
            "file_id": str(file_id),
            "source": {
                "file_name": "x.pdf",
                "file_hash": "h",
                "upload_date": "2024-01-01",
            },
        },
        "sections": [
            {
                "section_id": section_id,
                "file_id": str(file_id),
                "heading": "H",
                "section_type": "text",
                "content": "Short content.",
            }
        ],
    }

    with patch("app.extraction.document_analyzer.create_llm_client") as m_create:
        from unittest.mock import AsyncMock

        mock_client = MagicMock()
        mock_client.agenerate = AsyncMock(
            return_value=json.dumps(
                {
                    "heading": "H",
                    "content": "Short content.",
                    "section_summary": "Summary.",
                    "keywords": ["kw1"],
                }
            )
        )
        mock_client.generate = MagicMock(
            return_value=json.dumps(
                {
                    "document_type": "SOP",
                    "risk_level": "Informational",
                    "audience": ["Operator"],
                    "state": "Draft",
                    "technical_context": {
                        "equipment": None,
                        "version": None,
                        "workflow": [],
                    },
                    "effective_date": None,
                    "owner_team": None,
                    "supersedes_file_id": None,
                    "keywords": ["kw1"],
                    "keywords_hierarchy": {
                        "core_workflow_terms": ["kw1"],
                        "technologies": [],
                        "biological_materials": [],
                        "critical_process_steps": [],
                        "regulatory_or_qc_terms": [],
                    },
                }
            )
        )
        m_create.return_value = mock_client

        analyzer = DocumentSectionAnalyzer(
            preset="gemini-flash",
            config=MagicMock(
                temperature=0.2,
                max_tokens=4096,
                top_p=1.0,
                timeout=120.0,
                max_retries=3,
            ),
            max_concurrent=2,
        )
        result = analyzer.process_document(input_json)

    assert "sections" in result
    assert len(result["sections"]) == 1
    sec = result["sections"][0]
    assert sec["section_id"] == section_id
    assert sec["file_id"] == str(file_id)
    assert result["document"]["file_id"] == str(file_id)
