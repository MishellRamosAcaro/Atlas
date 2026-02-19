"""Tests for extractions API."""

import io
import tempfile
import uuid

import pytest
import httpx

from app.infrastructure.database import get_db
from app.main import app
from app.middleware.auth import get_current_user_id
from app.models.file import FILE_STATUS_CLEAN, FILE_STATUS_PENDING


@pytest.fixture
async def async_client():
    """Async client for extraction tests."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True,
    ) as ac:
        yield ac


@pytest.fixture
async def test_user_id(db_engine):
    """Create a user and return its id."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.repositories.user_repository import UserRepository

    maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with maker() as session:
        repo = UserRepository(session)
        user = await repo.create("extracttest@test.com", "Ext", "Test")
        await session.commit()
        return user.id


@pytest.fixture
async def override_get_db(db_engine):
    """Override get_db to use test engine."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async def _get_db():
        async with maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def auth_override(test_user_id):
    """Override get_current_user_id to return test user."""

    async def override():
        return test_user_id

    app.dependency_overrides[get_current_user_id] = override
    yield
    app.dependency_overrides.pop(get_current_user_id, None)


@pytest.fixture(autouse=True)
def extraction_storage_tmp(monkeypatch):
    """Use a temp dir for storage in extraction tests.

    Patch infrastructure, extraction_service, and uploads_service so that
    upload_and_extract flow (uploads then extractions) uses the same tmp dir.
    """
    from app.infrastructure.storage import FileSystemStorage

    with tempfile.TemporaryDirectory() as tmp:
        def _make_storage(base_path=tmp):
            return FileSystemStorage(base_path)

        monkeypatch.setattr(
            "app.infrastructure.storage.get_storage",
            lambda: _make_storage(),
        )
        monkeypatch.setattr(
            "app.services.extraction_service.get_storage",
            lambda: _make_storage(),
        )
        monkeypatch.setattr(
            "app.services.uploads_service.get_storage",
            lambda: _make_storage(),
        )
        yield tmp


@pytest.mark.asyncio
async def test_post_extractions_404_when_file_not_found(
    async_client, test_user_id, auth_override, override_get_db
):
    """POST /extractions/{file_id} returns 404 when file does not exist."""
    auth_override
    response = await async_client.post(f"/extractions/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_post_extractions_400_when_not_pdf(
    async_client, test_user_id, auth_override, override_get_db, db_engine
):
    """POST /extractions/{file_id} returns 400 when file is not PDF."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.repositories.files_repository import FilesRepository

    maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    file_id = uuid.uuid4()
    async with maker() as session:
        repo = FilesRepository(session)
        await repo.create_file(
            file_id=file_id,
            user_id=test_user_id,
            filename="doc.txt",
            stored_path=f"staging/{test_user_id}/{file_id}.txt",
            size_bytes=10,
            content_type="text/plain",
            status=FILE_STATUS_CLEAN,
        )
        await session.commit()

    # Storage must have the file so open() works; then service will reject by type
    import app.infrastructure.storage as storage_module

    storage = storage_module.get_storage()
    storage.save(b"hello", f"staging/{test_user_id}/{file_id}.txt")

    auth_override
    response = await async_client.post(f"/extractions/{file_id}")
    assert response.status_code == 400
    assert "Only PDF" in (response.json().get("detail") or "")


@pytest.mark.asyncio
async def test_post_extractions_400_when_not_clean(
    async_client, test_user_id, auth_override, override_get_db, db_engine
):
    """POST /extractions/{file_id} returns 400 when file status is not CLEAN."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.repositories.files_repository import FilesRepository

    maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    file_id = uuid.uuid4()
    async with maker() as session:
        repo = FilesRepository(session)
        await repo.create_file(
            file_id=file_id,
            user_id=test_user_id,
            filename="doc.pdf",
            stored_path=f"staging/{test_user_id}/{file_id}.pdf",
            size_bytes=100,
            content_type="application/pdf",
            status=FILE_STATUS_PENDING,
        )
        await session.commit()

    auth_override
    response = await async_client.post(f"/extractions/{file_id}")
    assert response.status_code == 400
    assert "not available" in (response.json().get("detail") or "").lower()


# Minimal valid PDF (single page with "Hello" text) for pipeline test
MINIMAL_PDF_BYTES = (
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


@pytest.mark.asyncio
async def test_post_extractions_200_returns_document_and_sections(
    async_client, test_user_id, auth_override, override_get_db, db_engine
):
    """POST /extractions/{file_id} returns 200 with document and sections for a valid PDF."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.repositories.files_repository import FilesRepository

    maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    file_id = uuid.uuid4()
    async with maker() as session:
        repo = FilesRepository(session)
        await repo.create_file(
            file_id=file_id,
            user_id=test_user_id,
            filename="sample.pdf",
            stored_path=f"staging/{test_user_id}/{file_id}.pdf",
            size_bytes=len(MINIMAL_PDF_BYTES),
            content_type="application/pdf",
            status=FILE_STATUS_CLEAN,
        )
        await session.commit()

    # Use module ref so we get the patched get_storage (same tmp as service)
    import app.infrastructure.storage as storage_module

    storage = storage_module.get_storage()
    storage.save(MINIMAL_PDF_BYTES, f"staging/{test_user_id}/{file_id}.pdf")

    auth_override
    response = await async_client.post(f"/extractions/{file_id}")
    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "document" in data
    assert "sections" in data
    assert "file_id" in data["document"]
    assert "source" in data["document"]
    assert isinstance(data["sections"], list)
    # Public response must not expose extraction_confidence
    for sec in data["sections"]:
        assert "extraction_confidence" not in sec


# --- POST /upload-and-extract (upload then extract in one call) ---


@pytest.mark.asyncio
async def test_post_upload_and_extract_200_returns_document_fields_only(
    async_client, test_user_id, auth_override, override_get_db
):
    """POST /upload-and-extract returns 200 with document fields only (no sections)."""
    auth_override
    response = await async_client.post(
        "/upload-and-extract",
        files={
            "file": (
                "sample.pdf",
                io.BytesIO(MINIMAL_PDF_BYTES),
                "application/pdf",
            )
        },
    )
    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "document" in data
    doc = data["document"]
    assert "file_id" in doc
    assert "source" in doc
    assert "document_type" in doc
    assert "technical_context" in doc
    assert "risk_level" in doc
    assert "audience" in doc
    assert "state" in doc
    assert "effective_date" in doc
    assert "owner_team" in doc
    assert "sections" not in data


@pytest.mark.asyncio
async def test_post_upload_and_extract_400_when_not_pdf(
    async_client, test_user_id, auth_override, override_get_db
):
    """POST /upload-and-extract returns 400 when file is not PDF."""
    auth_override
    response = await async_client.post(
        "/upload-and-extract",
        files={
            "file": (
                "doc.txt",
                io.BytesIO(b"hello world"),
                "text/plain",
            )
        },
    )
    assert response.status_code == 400
    assert "Only PDF" in (response.json().get("detail") or "")


# --- GET /extractions/{file_id}/document ---


@pytest.mark.asyncio
async def test_get_document_404_when_file_not_found(
    async_client, auth_override, override_get_db
):
    """GET /extractions/{file_id}/document returns 404 when file does not exist."""
    auth_override
    response = await async_client.get(
        f"/extractions/{uuid.uuid4()}/document",
    )
    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_document_404_when_no_extraction(
    async_client, test_user_id, auth_override, override_get_db, db_engine
):
    """GET /extractions/{file_id}/document returns 404 when file has no extraction."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.repositories.files_repository import FilesRepository

    maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    file_id = uuid.uuid4()
    async with maker() as session:
        repo = FilesRepository(session)
        await repo.create_file(
            file_id=file_id,
            user_id=test_user_id,
            filename="sample.pdf",
            stored_path=f"staging/{test_user_id}/{file_id}.pdf",
            size_bytes=100,
            content_type="application/pdf",
            status=FILE_STATUS_CLEAN,
        )
        await session.commit()

    auth_override
    response = await async_client.get(f"/extractions/{file_id}/document")
    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_get_document_200_returns_document(
    async_client, test_user_id, auth_override, override_get_db, db_engine
):
    """GET /extractions/{file_id}/document returns 200 with document when extraction exists."""
    import json as json_module

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.repositories.files_repository import FilesRepository

    maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    file_id = uuid.uuid4()
    relative_path = f"staging/{test_user_id}/extractions/{file_id}.json"
    async with maker() as session:
        repo = FilesRepository(session)
        await repo.create_file(
            file_id=file_id,
            user_id=test_user_id,
            filename="sample.pdf",
            stored_path=f"staging/{test_user_id}/{file_id}.pdf",
            size_bytes=100,
            content_type="application/pdf",
            status=FILE_STATUS_CLEAN,
        )
        await repo.update_extracted_doc_path(file_id, test_user_id, relative_path)
        await session.commit()

    import app.infrastructure.storage as storage_module

    storage = storage_module.get_storage()
    doc = {"file_id": str(file_id), "source": "sample.pdf", "title": "Test"}
    payload = {"document": doc, "sections": []}
    storage.save(
        json_module.dumps(payload).encode("utf-8"),
        relative_path,
    )

    auth_override
    response = await async_client.get(f"/extractions/{file_id}/document")
    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "document" in data
    doc = data["document"]
    assert doc.get("file_id") == str(file_id)
    assert doc.get("source") == "sample.pdf"
    assert "document_type" in doc
    assert "technical_context" in doc
    assert "risk_level" in doc
    assert "audience" in doc
    assert "state" in doc
    assert "effective_date" in doc
    assert "owner_team" in doc
