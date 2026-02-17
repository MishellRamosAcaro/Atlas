"""Pytest fixtures."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Load .env from project root (Atlas/) so DATABASE_URL_TEST is available
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

os.environ["ENV"] = "dev"
os.environ["JWT_SECRET_KEY"] = "test-secret"

from app.infrastructure.base import Base
from app.models import (  # noqa: F401 - register models for metadata
    File,
    LoginLockout,
    OAuthIdentity,
    RefreshToken,
    User,
)

DATABASE_URL_TEST = os.getenv("DATABASE_URL_TEST")
if not DATABASE_URL_TEST:
    raise EnvironmentError(
        "DATABASE_URL_TEST is not defined. "
        "Set the environment variable or add it to your .env file. "
        "Example: postgresql+asyncpg://postgres:postgres@localhost:5432/atlas_test"
    )
os.environ["DATABASE_URL"] = DATABASE_URL_TEST


@pytest.fixture
def anyio_backend():
    """Use asyncio backend for anyio."""
    return "asyncio"


@pytest.fixture
async def db_engine():
    """Create async engine for tests."""
    engine = create_async_engine(DATABASE_URL_TEST, echo=False)
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
