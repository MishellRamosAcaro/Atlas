"""Port interface for binary file storage used by application use cases."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageError(Exception):
    """Generic storage operation failure raised at the application boundary."""

    pass


class StoragePort(ABC):
    """Abstract interface for file storage backends."""

    @abstractmethod
    def save(self, content: bytes | BinaryIO, relative_path: str) -> str: ...

    @abstractmethod
    def open(self, relative_path: str) -> BinaryIO: ...

    @abstractmethod
    def delete(self, relative_path: str) -> None: ...

    @abstractmethod
    def exists(self, relative_path: str) -> bool: ...

    @abstractmethod
    def move(self, src_path: str, dst_path: str) -> str: ...
