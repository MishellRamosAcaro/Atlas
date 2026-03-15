"""Atlas FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.config import get_settings  # noqa: E402
from app.infrastructure.database import engine  # noqa: E402
from app.infrastructure.base import Base  # noqa: E402
from app.models import (  # noqa: F401, E402 - register models
    File,
    LoginLockout,
    RefreshToken,
    User,
    UserAccountStatus,
)
from app.routers import (  # noqa: E402
    auth,
    contact,
    enrichments,
    extractions,
    upload_extract_enrichment,
    uploads,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Startup: create tables (for MVP; use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="Atlas API",
    description="Atlas backend API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.env == "dev" else None,
    redoc_url="/redoc" if settings.env == "dev" else None,
)

# CORS: open in dev, restricted in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Rate limiting (SlowAPI) - per IP for MVP
from app.limiter import limiter  # noqa: E402

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers
from app.middleware.security_headers import SecurityHeadersMiddleware  # noqa: E402

app.add_middleware(SecurityHeadersMiddleware)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(uploads.router, prefix="/uploads", tags=["Uploads"])
app.include_router(extractions.router, prefix="/extractions", tags=["Extractions"])
app.include_router(enrichments.router, prefix="/enrichments", tags=["Enrichments"])
app.include_router(contact.router, prefix="/contact", tags=["Contact"])
app.include_router(
    upload_extract_enrichment.router,
    prefix="/upload-extract-enrichment",
    tags=["Upload, extract and enrichment"],
)
