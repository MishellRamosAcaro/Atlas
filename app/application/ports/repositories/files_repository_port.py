"""Port interface for file persistence operations used in use cases."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any


class FilesRepositoryPort(ABC):
    """Abstract interface for working with file records."""

    @abstractmethod
    async def create_file(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID,
        filename: str,
        stored_path: str,
        size_bytes: int,
        content_type: str,
        status: str,
        scan_provider: str,
    ) -> Any: ...

    @abstractmethod
    async def count_files_by_user(self, user_id: uuid.UUID) -> int: ...

    @abstractmethod
    async def list_files_by_user(
        self,
        user_id: uuid.UUID,
        include_pending: bool = True,
    ) -> list[Any]: ...

    @abstractmethod
    async def list_all_files_by_user(self, user_id: uuid.UUID) -> list[Any]: ...

    @abstractmethod
    async def get_file_by_id(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> Any | None: ...

    @abstractmethod
    async def update_file_status(
        self,
        file_id: uuid.UUID,
        status: str,
        scan_result: str | None = None,
    ) -> Any | None: ...

    @abstractmethod
    async def delete_file_record(
        self, file_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool: ...

    @abstractmethod
    async def update_extracted_doc_path(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID,
        relative_path: str,
    ) -> bool: ...

    @abstractmethod
    async def update_filename(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID,
        filename: str,
    ) -> bool: ...
