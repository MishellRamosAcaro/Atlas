"""Unit tests for extraction pipeline (no DB)."""

import uuid

import pytest

from app.extraction.pipeline import extract_document
from app.extraction.schemas import SectionSchema

# Minimal valid PDF (single page)
MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
    b"/Contents 4 0 R >>\nendobj\n"
    b"4 0 obj\n<< /Length 44 >>\nstream\n"
    b"BT\n/F1 12 Tf\n100 700 Td\n(Hello world)\nTj\nET\nendstream\nendobj\n"
    b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n"
    b"0000000058 00000 n \n0000000115 00000 n \n0000000206 00000 n \n"
    b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n297\n%%EOF"
)


def test_extract_document_returns_document_and_sections():
    """extract_document returns (DocumentSchema, list[SectionSchema])."""
    test_file_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    doc, sections = extract_document(
        MINIMAL_PDF,
        "test.pdf",
        "application/pdf",
        file_id=test_file_id,
        include_keywords=True,
    )
    assert doc.file_id == test_file_id
    assert doc.source.file_name == "test.pdf"
    assert doc.source.file_hash
    assert doc.source.upload_date
    assert isinstance(doc.sections, list)
    assert isinstance(sections, list)


def test_extract_document_section_model_dump_public_excludes_confidence():
    """Section model_dump_public() must not include extraction_confidence."""
    _, sections = extract_document(
        MINIMAL_PDF,
        "test.pdf",
        "application/pdf",
        file_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        include_keywords=False,
    )
    for sec in sections:
        assert isinstance(sec, SectionSchema)
        public = sec.model_dump_public()
        assert "extraction_confidence" not in public


def test_extract_document_rejects_non_pdf():
    """extract_document raises ValueError for non-PDF content_type."""
    with pytest.raises(ValueError, match="Unsupported type"):
        extract_document(
            b"not a pdf",
            "x.txt",
            "text/plain",
            file_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        )
