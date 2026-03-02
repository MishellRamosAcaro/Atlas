"""Port interface for refresh token persistence operations."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class RefreshTokenRepositoryPort(ABC):
    """Abstract interface for refresh token repository operations."""

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> Any | None:
        ...

    @abstractmethod
    async def count_active_by_user(self, user_id: uuid.UUID) -> int:
        ...

    @abstractmethod
    async def create(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
        client_ip: str | None = None,
    ) -> Any:
        ...

    @abstractmethod
    async def delete_by_id(self, token_id: uuid.UUID) -> None:
        ...

    @abstractmethod
    async def delete_by_token_hash(self, token_hash: str) -> None:
        ...

    @abstractmethod
    async def delete_all_by_user(self, user_id: uuid.UUID) -> None:
        ...

    @abstractmethod
    async def delete_oldest_for_user(self, user_id: uuid.UUID) -> None:
        ...

    @abstractmethod
    async def update_last_used(
        self,
        token: Any,
        last_used_at: datetime | None = None,
    ) -> None:
        ...

