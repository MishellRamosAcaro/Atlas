"""Port interface for OAuth identity persistence operations."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any


class OAuthIdentityRepositoryPort(ABC):
    """Abstract interface for OAuth identity repository operations."""

    @abstractmethod
    async def get_by_provider_user(
        self,
        provider: str,
        provider_user_id: str,
    ) -> Any | None:
        ...

    @abstractmethod
    async def create(
        self,
        user_id: uuid.UUID,
        provider: str,
        provider_user_id: str,
    ) -> Any:
        ...

