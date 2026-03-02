"""Port interface for login lockout persistence and rules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LoginLockoutRepositoryPort(ABC):
    """Abstract interface for login lockout repository operations."""

    @abstractmethod
    async def get_by_email(self, email: str) -> Any | None:
        ...

    @abstractmethod
    def is_locked(self, record: Any | None) -> tuple[bool, int | None]:
        ...

    @abstractmethod
    async def record_failed_attempt(self, email: str) -> Any:
        ...

    @abstractmethod
    async def clear(self, email: str) -> None:
        ...

