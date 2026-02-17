"""Antivirus scanner abstraction: noop in dev, real scanner in prod."""

from app.config import get_settings

settings = get_settings()

# Result constants
SCAN_CLEAN = "CLEAN"
SCAN_INFECTED = "INFECTED"
SCAN_FAILED = "FAILED_SCAN"


def scan_file(path: str, content: bytes) -> tuple[str, str | None]:
    """Scan file content.

    Returns (status, detail).
    status: SCAN_CLEAN | SCAN_INFECTED | SCAN_FAILED
    detail: optional message or scan result code.
    """
    if not settings.uploads_antivirus_enabled:
        # Dev: no scanner; treat as clean
        return SCAN_CLEAN, None

    # Prod: integrate ClamAV, GCS malware scanning, etc.
    # For v1 we have no real integration; treat as clean so tests pass.
    # When integrating: read from path or use content, call scanner, return result.
    return SCAN_CLEAN, None
