"""Port interface for LLM clients used by application use cases."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClientPort(ABC):
    """Abstract interface for large language model clients."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Synchronous generation."""
        ...

    @abstractmethod
    async def agenerate(self, prompt: str) -> str:
        """Asynchronous generation."""
        ...
