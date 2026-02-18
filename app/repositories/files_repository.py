"""Files repository: DB-only CRUD for file upload records."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import (
    FILE_STATUS_CLEAN,
    FILE_STATUS_PENDING,
    File,
)


class FilesRepository:
    """Repository for File entity (DB only)."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self._session = session

    async def create_file(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID,
        filename: str,
        stored_path: str,
        size_bytes: int,
        content_type: str,
        status: str = FILE_STATUS_PENDING,
        scan_provider: str = "",
    ) -> File:
        """Create a new file record."""
        file_record = File(
            file_id=file_id,
            user_id=user_id,
            filename=filename,
            stored_path=stored_path,
            size_bytes=size_bytes,
            content_type=content_type,
            status=status,
            scan_provider=scan_provider,
        )
        self._session.add(file_record)
        await self._session.flush()
        return file_record

    async def count_files_by_user(self, user_id: uuid.UUID) -> int:
        """Count files owned by user (all statuses for quota)."""
        result = await self._session.execute(
            select(func.count(File.file_id)).where(File.user_id == user_id)
        )
        return result.scalar() or 0

    async def list_files_by_user(
        self,
        user_id: uuid.UUID,
        include_pending: bool = True,
    ) -> list[File]:
        """List files for user. Only CLEAN by default; set include_pending for PENDING_SCAN."""
        statuses = [FILE_STATUS_CLEAN]
        if include_pending:
            statuses.append(FILE_STATUS_PENDING)
        result = await self._session.execute(
            select(File)
            .where(File.user_id == user_id)
            .where(File.status.in_(statuses))
            .order_by(File.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_file_by_id(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> File | None:
        """Get file by id. If user_id given, only return if owned by that user."""
        q = select(File).where(File.file_id == file_id)
        if user_id is not None:
            q = q.where(File.user_id == user_id)
        result = await self._session.execute(q)
        return result.scalar_one_or_none()

    async def update_file_status(
        self,
        file_id: uuid.UUID,
        status: str,
        scan_result: str | None = None,
    ) -> File | None:
        """Update file status (e.g. PENDING_SCAN -> CLEAN)."""
        file_record = await self.get_file_by_id(file_id)
        if not file_record:
            return None
        file_record.status = status
        if scan_result is not None:
            file_record.scan_result = scan_result
        file_record.scanned_at = datetime.now(timezone.utc)
        self._session.add(file_record)
        await self._session.flush()
        return file_record

    async def delete_file_record(self, file_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete file record if it belongs to user. Returns True if deleted."""
        file_record = await self.get_file_by_id(file_id, user_id=user_id)
        if not file_record:
            return False
        await self._session.delete(file_record)
        await self._session.flush()
        return True

    async def update_extracted_doc_path(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID,
        relative_path: str,
    ) -> bool:
        """Update extracted_doc_path for the file if owned by user. Returns True if updated."""
        file_record = await self.get_file_by_id(file_id, user_id=user_id)
        if not file_record:
            return False
        file_record.extracted_doc_path = relative_path
        self._session.add(file_record)
        await self._session.flush()
        return True
