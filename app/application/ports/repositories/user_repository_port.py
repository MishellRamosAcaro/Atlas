"""Port interface for user persistence operations."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any


class UserRepositoryPort(ABC):
    """Abstract interface for user repository operations."""

    @abstractmethod
    async def get_by_email(self, email: str) -> Any | None: ...

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> Any | None: ...

    @abstractmethod
    async def create_user(self, email: str, password_hash: str | None) -> Any: ...

    @abstractmethod
    async def delete_user(self, user_id: uuid.UUID) -> None: ...
