"""Storage abstraction for file uploads: filesystem (dev) or GCS (prod)."""

from pathlib import Path
from typing import BinaryIO

from app.config import get_settings

settings = get_settings()


class StorageError(Exception):
    """Storage operation failed."""

    pass


class FileSystemStorage:
    """Store files on local filesystem. Used in dev."""

    def __init__(self, base_path: str | None = None) -> None:
        """Initialize with base directory (default from settings)."""
        self._base = Path(base_path or settings.uploads_storage_path)
        self._base.mkdir(parents=True, exist_ok=True)

    def _full_path(self, relative_path: str) -> Path:
        """Resolve full path; ensure it is under base (no escape)."""
        full = (self._base / relative_path).resolve()
        if not str(full).startswith(str(self._base.resolve())):
            raise StorageError("Invalid path")
        return full

    def save(self, content: bytes | BinaryIO, relative_path: str) -> str:
        """Save content at relative_path. Creates parent dirs. Returns stored_path (same as relative_path)."""
        full = self._full_path(relative_path)
        full.parent.mkdir(parents=True, exist_ok=True)
        with open(full, "wb") as f:
            if isinstance(content, bytes):
                f.write(content)
            else:
                f.write(content.read())
        return relative_path

    def open(self, relative_path: str) -> BinaryIO:
        """Open file for reading. Returns file-like object."""
        full = self._full_path(relative_path)
        if not full.is_file():
            raise StorageError("File not found")
        return open(full, "rb")

    def delete(self, relative_path: str) -> None:
        """Delete file at relative_path. No-op if missing."""
        full = self._full_path(relative_path)
        if full.is_file():
            full.unlink()

    def exists(self, relative_path: str) -> bool:
        """Check if file exists."""
        return self._full_path(relative_path).is_file()

    def move(self, src_path: str, dst_path: str) -> str:
        """Move file from src_path to dst_path. Returns dst_path."""
        src = self._full_path(src_path)
        dst = self._full_path(dst_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not src.is_file():
            raise StorageError("Source file not found")
        src.rename(dst)
        return dst_path


def get_storage() -> FileSystemStorage:
    """Return storage implementation. For v1 always filesystem; later switch to GCS in prod."""
    return FileSystemStorage()
