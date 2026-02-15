"""Pytest fixtures."""

import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ["ENV"] = "dev"
os.environ["JWT_SECRET_KEY"] = "test-secret"

from app.infrastructure.base import Base
from app.models import OAuthIdentity, RefreshToken, User  # noqa: F401 - register models

DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/atlas_test",
)


@pytest.fixture
def anyio_backend():
    """Use asyncio backend for anyio."""
    return "asyncio"


@pytest.fixture
async def db_engine():
    """Create async engine for tests."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create async session for tests."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with async_session() as session:
        yield session
        await session.rollback()
