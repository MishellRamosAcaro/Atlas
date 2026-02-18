"""Uploads service: validation, storage, scan, and DB orchestration."""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.infrastructure.antivirus_scanner import (
    SCAN_CLEAN,
    SCAN_INFECTED,
    scan_file,
)
from app.infrastructure.storage import FileSystemStorage, get_storage
from app.models.file import FILE_STATUS_CLEAN, FILE_STATUS_PENDING
from app.repositories.files_repository import FilesRepository

MAX_FILE_SIZE_BYTES = 3 * 1024 * 1024  # 3 MB
MAX_FILES_PER_USER = 5
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


def _get_extension(filename: str) -> str:
    """Return lower extension including dot."""
    return Path(filename).suffix.lower()


def _validate_file_type(filename: str, content_type: str) -> None:
    """Validate extension and MIME. Raise 400 if invalid."""
    ext = _get_extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Allowed types: .pdf, .docx, .txt",
        )
    if content_type and content_type.split(";")[0].strip() not in ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type.",
        )


def _validate_file_size(size: int) -> None:
    """Validate size. Raise 413 if too large."""
    if size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File size must be under 3MB.",
        )


class UploadsService:
    """Service for file upload flow: validate, store, scan, persist."""

    def __init__(
        self,
        files_repo: FilesRepository,
        storage: FileSystemStorage | None = None,
    ) -> None:
        """Initialize with repository and optional storage (default from get_storage)."""
        self._repo = files_repo
        self._storage = storage or get_storage()

    async def upload_file(
        self,
        user_id: uuid.UUID,
        file: UploadFile,
    ) -> tuple[uuid.UUID, bool]:
        """Process upload: validate, save to staging, create record, scan, confirm or cleanup.

        Returns (file_id, ok). If infected, record and file are removed and ok=False
        (caller should raise 400). If ok=True, returns file_id for response.
        """
        filename = file.filename or "unnamed"
        content_type = file.content_type or ""
        content = await file.read()
        size = len(content)

        _validate_file_type(filename, content_type)
        _validate_file_size(size)

        count = await self._repo.count_files_by_user(user_id)
        if count >= MAX_FILES_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have reached the limit of 5 files.",
            )

        file_id = uuid.uuid4()
        ext = _get_extension(filename) or ".bin"
        staging_path = f"staging/{user_id}/{file_id}{ext}"

        self._storage.save(content, staging_path)
        await self._repo.create_file(
            file_id=file_id,
            user_id=user_id,
            filename=filename,
            stored_path=staging_path,
            size_bytes=size,
            content_type=content_type,
            status=FILE_STATUS_PENDING,
            scan_provider="",
        )

        scan_status, scan_detail = scan_file(staging_path, content)

        if scan_status == SCAN_INFECTED:
            self._storage.delete(staging_path)
            await self._repo.delete_file_record(file_id, user_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archivo rechazado por seguridad.",
            )

        if scan_status == SCAN_CLEAN:
            await self._repo.update_file_status(file_id, FILE_STATUS_CLEAN, scan_detail)

        return file_id, True

    async def list_files(self, user_id: uuid.UUID, include_pending: bool = True):
        """List user files (CLEAN and optionally PENDING_SCAN)."""
        return await self._repo.list_files_by_user(
            user_id, include_pending=include_pending
        )

    async def get_file_metadata(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """Get file metadata if owned by user."""
        return await self._repo.get_file_by_id(file_id, user_id=user_id)

    async def get_file_for_download(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """Get file record only if CLEAN and owned by user (for streaming download)."""
        file_record = await self._repo.get_file_by_id(file_id, user_id=user_id)
        if not file_record or file_record.status != FILE_STATUS_CLEAN:
            return None
        return file_record

    async def delete_file(self, file_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete file from storage and DB if owned by user. Returns True if deleted."""
        file_record = await self._repo.get_file_by_id(file_id, user_id=user_id)
        if not file_record:
            return False
        self._storage.delete(file_record.stored_path)
        return await self._repo.delete_file_record(file_id, user_id)
