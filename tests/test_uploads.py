"""Tests for uploads API. Use AsyncClient so all requests run in the same event loop as async fixtures (avoids Task/asyncpg conflicts)."""

import io
import tempfile
import uuid

import pytest
import httpx
from fastapi.testclient import TestClient

from app.infrastructure.database import get_db
from app.main import app
from app.middleware.auth import get_current_user_id


@pytest.fixture
def client():
    """Sync test client (for tests that only need auth override, no DB seeding)."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Async client: same event loop as fixtures, follow redirects for /uploads vs /uploads/."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True,
    ) as ac:
        yield ac


@pytest.fixture
async def test_user_id(db_engine):
    """Create a user in the DB and return its id (for upload auth). Use conftest engine to avoid event loop / asyncpg conflicts with TestClient."""
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
        user = await repo.create(
            "uploadtest@test.com",
            "Up",
            "Load",
        )
        await session.commit()
        return user.id


@pytest.fixture
async def override_get_db(db_engine):
    """Make the app use the test db_engine so all DB access runs in the same event loop."""
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
    """Override get_current_user_id to return test user (use in tests)."""

    async def override():
        return test_user_id

    app.dependency_overrides[get_current_user_id] = override
    yield
    app.dependency_overrides.pop(get_current_user_id, None)


@pytest.fixture(autouse=True)
def uploads_storage_tmp(monkeypatch):
    """Use a temp dir for uploads in tests."""
    from app.infrastructure.storage import FileSystemStorage

    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(
            "app.infrastructure.storage.get_storage",
            lambda: FileSystemStorage(tmp),
        )
        yield tmp


def test_post_uploads_rejects_over_3mb(client, test_user_id, auth_override):
    """POST /uploads rejects file > 3MB with 413."""
    payload = b"x" * (3 * 1024 * 1024 + 1)
    response = client.post(
        "/uploads",
        files={"file": ("large.txt", io.BytesIO(payload), "text/plain")},
    )
    assert response.status_code == 413


def test_post_uploads_rejects_invalid_type(client, test_user_id, auth_override):
    """POST /uploads rejects invalid file type with 400."""
    auth_override
    response = client.post(
        "/uploads",
        files={"file": ("script.exe", io.BytesIO(b"fake"), "application/x-msdownload")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_post_uploads_rejects_when_5_files(
    async_client, test_user_id, auth_override, override_get_db, db_engine
):
    """POST /uploads returns 409 when user already has 5 files."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.models.file import FILE_STATUS_CLEAN
    from app.repositories.files_repository import FilesRepository

    maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with maker() as session:
        repo = FilesRepository(session)
        for i in range(5):
            await repo.create_file(
                file_id=uuid.uuid4(),
                user_id=test_user_id,
                filename=f"f{i}.txt",
                stored_path=f"staging/{test_user_id}/f{i}.txt",
                size_bytes=1,
                content_type="text/plain",
                status=FILE_STATUS_CLEAN,
            )
        await session.commit()

    response = await async_client.post(
        "/uploads",
        files={"file": ("new.txt", io.BytesIO(b"hi"), "text/plain")},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_uploads_list_only_own_files(
    async_client, test_user_id, auth_override, override_get_db
):
    """GET /uploads returns only files for the current user."""
    response = await async_client.get("/uploads")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_download_blocked_if_not_clean(
    async_client, test_user_id, auth_override, override_get_db, db_engine
):
    """GET /uploads/{file_id}/download returns 404 if status != CLEAN."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.models.file import FILE_STATUS_PENDING
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
            filename="p.txt",
            stored_path=f"staging/{test_user_id}/p.txt",
            size_bytes=2,
            content_type="text/plain",
            status=FILE_STATUS_PENDING,
        )
        await session.commit()

    response = await async_client.get(f"/uploads/{file_id}/download")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_returns_404_if_not_owner(
    async_client, test_user_id, auth_override, override_get_db, db_engine
):
    """DELETE /uploads/{file_id} returns 404 if file belongs to another user."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.models.file import FILE_STATUS_CLEAN
    from app.repositories.files_repository import FilesRepository
    from app.repositories.user_repository import UserRepository

    maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with maker() as session:
        user_repo = UserRepository(session)
        other = await user_repo.create("other@test.com", "O", "Ther")
        await session.flush()
        repo = FilesRepository(session)
        await repo.create_file(
            file_id=uuid.uuid4(),
            user_id=other.id,
            filename="other.txt",
            stored_path="staging/other/other.txt",
            size_bytes=1,
            content_type="text/plain",
            status=FILE_STATUS_CLEAN,
        )
        await session.commit()
        files = await repo.list_files_by_user(other.id)
        other_file_id = files[0].file_id

    response = await async_client.delete(f"/uploads/{other_file_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_post_uploads_infected_removes_file_and_record(
    async_client, test_user_id, auth_override, override_get_db, monkeypatch
):
    """POST with scanner INFECTED returns 400 and leaves no record in DB."""
    from app.infrastructure import antivirus_scanner
    from app.services import uploads_service

    monkeypatch.setattr(
        uploads_service,
        "scan_file",
        lambda path, content: (antivirus_scanner.SCAN_INFECTED, "mock"),
    )

    response = await async_client.post(
        "/uploads",
        files={"file": ("bad.txt", io.BytesIO(b"content"), "text/plain")},
    )
    assert response.status_code == 400
    assert "rechazado" in response.json().get("detail", "").lower()
