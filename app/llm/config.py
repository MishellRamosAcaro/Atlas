"""LLM configuration: single source of truth for model parameters."""

from __future__ import annotations

import os
from dataclasses import dataclass


class LLMConfigError(Exception):
    """Raised when a required LLM env var is missing or invalid."""


@dataclass
class LLMConfig:
    """
    Global LLM configuration. All values are read from .env; there are no
    in-code defaults. Use from_env() to build from environment variables.
    Constructor args can be used to override after loading (e.g. from request body).
    """

    temperature: float
    max_tokens: int
    top_p: float
    timeout: float
    max_retries: int

    @classmethod
    def from_env(cls) -> LLMConfig:
        """Build config from environment variables only. Raises LLMConfigError if any var is missing or invalid."""
        return cls(
            temperature=_required_float_from_env("LLM_TEMPERATURE"),
            max_tokens=_required_int_from_env("LLM_MAX_TOKENS"),
            top_p=_required_float_from_env("LLM_TOP_P"),
            timeout=_required_float_from_env("LLM_TIMEOUT"),
            max_retries=_required_int_from_env("LLM_MAX_RETRIES"),
        )


def _required_float_from_env(name: str) -> float:
    raw = os.environ.get(name)
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        raise LLMConfigError(
            f"Missing required env var: {name}. Set it in .env (e.g. in the LLM tuning section)."
        )
    try:
        return float(raw)
    except ValueError as e:
        raise LLMConfigError(
            f"Invalid value for {name}: {raw!r}. Must be a number."
        ) from e


def _required_int_from_env(name: str) -> int:
    raw = os.environ.get(name)
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        raise LLMConfigError(
            f"Missing required env var: {name}. Set it in .env (e.g. in the LLM tuning section)."
        )
    try:
        return int(raw)
    except ValueError as e:
        raise LLMConfigError(
            f"Invalid value for {name}: {raw!r}. Must be an integer."
        ) from e
