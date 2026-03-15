"""Tests for enrichments API. Require Postgres (DATABASE_URL_TEST in .env)."""

import json
import uuid

import httpx
import pytest

from app.infrastructure.database import get_db
from app.main import app
from app.middleware.auth import get_current_user_id
from app.models.file import FILE_STATUS_CLEAN


@pytest.fixture
async def async_client():
    """Async HTTP client for enrichment tests."""
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
        user = await repo.create("enrichmenttest@test.com", "Enrich", "Test")
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
def enrichment_storage_tmp(monkeypatch):
    """Use a temp dir for storage in enrichment tests."""
    import tempfile

    from app.infrastructure.storage import FileSystemStorage

    with tempfile.TemporaryDirectory() as tmp:

        def _get_storage():
            return FileSystemStorage(tmp)

        monkeypatch.setattr(
            "app.infrastructure.storage.get_storage",
            _get_storage,
        )
        monkeypatch.setattr(
            "app.services.enrichment_service.get_storage",
            _get_storage,
        )
        yield tmp


@pytest.mark.asyncio
async def test_post_enrichments_404_when_file_not_found(
    async_client, test_user_id, auth_override, override_get_db
):
    """POST /enrichments/{file_id} returns 404 when file does not exist."""
    auth_override
    response = await async_client.post(f"/enrichments/{uuid.uuid4()}")
    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_post_enrichments_404_when_no_extraction(
    async_client, test_user_id, auth_override, override_get_db, db_engine
):
    """POST /enrichments/{file_id} returns 404 when file has no extraction."""
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
    response = await async_client.post(f"/enrichments/{file_id}")
    assert response.status_code == 404
    detail = response.json().get("detail") or ""
    assert "extraction" in detail.lower() or "not found" in detail.lower()


@pytest.mark.asyncio
async def test_post_enrichments_200_returns_document_and_sections(
    async_client, test_user_id, auth_override, override_get_db, db_engine, monkeypatch
):
    """POST /enrichments/{file_id} returns 200 with document and sections when extraction exists (LLM mocked)."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.repositories.files_repository import FilesRepository

    file_id = uuid.uuid4()
    relative_path = f"staging/{test_user_id}/extractions/{file_id}.json"
    extraction_payload = {
        "document": {
            "file_id": str(file_id),
            "source": {
                "file_name": "sample.pdf",
                "file_hash": "h",
                "upload_date": "2024-01-01",
            },
        },
        "sections": [
            {
                "section_id": "sec-1",
                "file_id": str(file_id),
                "heading": "Intro",
                "section_type": "text",
                "content": "Short content.",
            }
        ],
    }
    enriched_document = {
        **extraction_payload["document"],
        "document_type": "SOP",
        "risk_level": "Informational",
        "keywords": [{"term": "term1", "score": 1.0}],
        "keywords_hierarchy": {},
    }
    enriched_sections = [
        {
            **extraction_payload["sections"][0],
            "section_summary": "Summary.",
            "keywords": [{"term": "kw1", "score": 1.0}],
        }
    ]
    mock_enriched = {"document": enriched_document, "sections": enriched_sections}

    async def _fake_to_thread(fn, *args):
        """Return mock result without calling real LLM (to_thread is awaited)."""
        return mock_enriched

    monkeypatch.setattr(
        "app.services.enrichment_service.asyncio.to_thread",
        _fake_to_thread,
    )

    maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
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
    storage.save(
        json.dumps(extraction_payload, ensure_ascii=False).encode("utf-8"),
        relative_path,
    )

    auth_override
    response = await async_client.post(
        f"/enrichments/{file_id}",
        json={"llm_preset": "gemini-flash"},
    )

    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "document" in data
    assert "sections" in data
    assert data["document"].get("document_type") == "SOP"
    assert len(data["sections"]) == 1
    assert data["sections"][0].get("section_summary") == "Summary."
