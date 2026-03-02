"""Port interface for antivirus / malware scanning used by uploads use cases."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable


SCAN_CLEAN = "CLEAN"
SCAN_INFECTED = "INFECTED"
SCAN_FAILED = "FAILED_SCAN"


@runtime_checkable
class ScanPort(Protocol):
    """Protocol for simple functional-style scanners."""

    def __call__(self, path: str, content: bytes) -> tuple[str, str | None]:
        ...


class ScannerPort(ABC):
    """Object-oriented antivirus port used by application layer."""

    @abstractmethod
    def scan_file(self, path: str, content: bytes) -> tuple[str, str | None]:
        ...

