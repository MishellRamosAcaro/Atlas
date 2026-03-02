"""LLM configuration: single source of truth for model parameters."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """
    Global LLM configuration.

    Resolution order: 1) constructor args, 2) environment variables,
    3) in-code defaults. Use from_env() to build from env; constructor
    values take precedence when passed explicitly.
    """

    temperature: float = 0.2
    max_tokens: int = 8192
    top_p: float = 1.0
    timeout: float = 120.0
    max_retries: int = 1

    @classmethod
    def from_env(cls) -> LLMConfig:
        """Build config from environment variables (and in-code defaults)."""
        return cls(
            temperature=_float_from_env("LLM_TEMPERATURE", 0.2),
            max_tokens=_int_from_env("LLM_MAX_TOKENS", 4096),
            top_p=_float_from_env("LLM_TOP_P", 1.0),
            timeout=_float_from_env("LLM_TIMEOUT", 120.0),
            max_retries=_int_from_env("LLM_MAX_RETRIES", 3),
        )


def _float_from_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_from_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default
