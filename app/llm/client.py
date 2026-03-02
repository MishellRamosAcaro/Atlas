"""Unified LLM client interface and provider implementations (native SDKs, no LangChain)."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any

from app.llm.config import LLMConfig


LLM_PRESETS = {
    "gemini-flash": "gemini-2.0-flash",
}
DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def _get_api_key(env_var: str, explicit: str | None) -> str | None:
    """Return explicit key or environment value."""
    return explicit or __import__("os").environ.get(env_var)


def _retry_sync(fn, max_retries: int, timeout: float) -> Any:
    """Run sync fn with timeout and exponential backoff."""
    import concurrent.futures

    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(fn)
                return fut.result(timeout=timeout)
        except concurrent.futures.TimeoutError as e:
            last_err = e
            if attempt < max_retries:
                time.sleep(2**attempt)
        except Exception as e:
            last_err = e
            if attempt < max_retries and _is_retryable(e):
                time.sleep(2**attempt)
            else:
                raise
    if last_err:
        raise last_err
    raise RuntimeError("Unexpected retry loop exit")


def _is_retryable(e: Exception) -> bool:
    """Whether to retry on this exception (e.g. 429, 5xx)."""
    err_str = str(e).lower()
    if "429" in err_str or "rate" in err_str:
        return True
    if "500" in err_str or "502" in err_str or "503" in err_str:
        return True
    return False


class BaseLLMClient(ABC):
    """Unified interface: receive prompt (str), return response (str)."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Synchronous generation."""
        ...

    @abstractmethod
    async def agenerate(self, prompt: str) -> str:
        """Asynchronous generation."""
        ...


class _AnthropicClient(BaseLLMClient):
    """Anthropic SDK (claude-haiku)."""

    def __init__(
        self,
        model_id: str,
        config: LLMConfig,
        api_key: str | None = None,
    ) -> None:
        self._model_id = model_id
        self._config = config
        self._api_key = _get_api_key("ANTHROPIC_API_KEY", api_key)
        if not self._api_key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY.")

    def generate(self, prompt: str) -> str:
        from anthropic import Anthropic

        client = Anthropic(
            api_key=self._api_key,
            timeout=self._config.timeout,
            max_retries=0,
        )

        def _call() -> str:
            r = client.messages.create(
                model=self._model_id,
                max_tokens=self._config.max_tokens,
                temperature=self._config.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return (r.content[0].text) if r.content else ""

        return _retry_sync(
            _call,
            self._config.max_retries,
            self._config.timeout,
        )

    async def agenerate(self, prompt: str) -> str:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(
            api_key=self._api_key,
            timeout=self._config.timeout,
            max_retries=0,
        )

        async def _call() -> str:
            r = await client.messages.create(
                model=self._model_id,
                max_tokens=self._config.max_tokens,
                temperature=self._config.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return (r.content[0].text) if r.content else ""

        return await _retry_async(
            _call,
            self._config.max_retries,
            self._config.timeout,
        )


class _GeminiClient(BaseLLMClient):
    """Google Generative AI SDK (gemini-flash)."""

    def __init__(
        self,
        model_id: str,
        config: LLMConfig,
        api_key: str | None = None,
    ) -> None:
        self._model_id = model_id
        self._config = config
        self._api_key = _get_api_key("GOOGLE_API_KEY", api_key)
        if not self._api_key:
            raise ValueError("Google API key required. Set GOOGLE_API_KEY.")

    def generate(self, prompt: str) -> str:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self._api_key)

        def _call() -> str:
            r = client.models.generate_content(
                model=self._model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self._config.temperature,
                    max_output_tokens=self._config.max_tokens,
                    top_p=self._config.top_p,
                ),
            )
            if r.text is None:
                return ""
            return r.text

        return _retry_sync(
            _call,
            self._config.max_retries,
            self._config.timeout,
        )

    async def agenerate(self, prompt: str) -> str:
        return await asyncio.to_thread(self.generate, prompt)


class _DeepSeekClient(BaseLLMClient):
    """OpenAI-compatible client for DeepSeek (base_url)."""

    def __init__(
        self,
        model_id: str,
        config: LLMConfig,
        api_key: str | None = None,
    ) -> None:
        self._model_id = model_id
        self._config = config
        self._api_key = _get_api_key("DEEPSEEK_API_KEY", api_key)
        if not self._api_key:
            raise ValueError("DeepSeek API key required. Set DEEPSEEK_API_KEY.")

    def generate(self, prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(
            api_key=self._api_key,
            base_url=DEEPSEEK_BASE_URL,
            timeout=self._config.timeout,
        )

        def _call() -> str:
            r = client.chat.completions.create(
                model=self._model_id,
                max_tokens=self._config.max_tokens,
                messages=[{"role": "user", "content": prompt}],
                temperature=self._config.temperature,
            )
            if not r.choices:
                return ""
            return r.choices[0].message.content or ""

        return _retry_sync(
            _call,
            self._config.max_retries,
            self._config.timeout,
        )

    async def agenerate(self, prompt: str) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=DEEPSEEK_BASE_URL,
            timeout=self._config.timeout,
        )

        async def _call() -> str:
            r = await client.chat.completions.create(
                model=self._model_id,
                max_tokens=self._config.max_tokens,
                messages=[{"role": "user", "content": prompt}],
                temperature=self._config.temperature,
            )
            if not r.choices:
                return ""
            return r.choices[0].message.content or ""

        return await _retry_async(
            _call,
            self._config.max_retries,
            self._config.timeout,
        )


class _OpenAIClient(BaseLLMClient):
    """OpenAI SDK (ChatGPT); uses default API, OPENAI_API_KEY."""

    def __init__(
        self,
        model_id: str,
        config: LLMConfig,
        api_key: str | None = None,
    ) -> None:
        self._model_id = model_id
        self._config = config
        self._api_key = _get_api_key("OPENAI_API_KEY", api_key)
        if not self._api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY.")

    def generate(self, prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(
            api_key=self._api_key,
            timeout=self._config.timeout,
        )

        def _call() -> str:
            r = client.chat.completions.create(
                model=self._model_id,
                max_tokens=self._config.max_tokens,
                messages=[{"role": "user", "content": prompt}],
                temperature=self._config.temperature,
            )
            if not r.choices:
                return ""
            return r.choices[0].message.content or ""

        return _retry_sync(
            _call,
            self._config.max_retries,
            self._config.timeout,
        )

    async def agenerate(self, prompt: str) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self._api_key,
            timeout=self._config.timeout,
        )

        async def _call() -> str:
            r = await client.chat.completions.create(
                model=self._model_id,
                max_tokens=self._config.max_tokens,
                messages=[{"role": "user", "content": prompt}],
                temperature=self._config.temperature,
            )
            if not r.choices:
                return ""
            return r.choices[0].message.content or ""

        return await _retry_async(
            _call,
            self._config.max_retries,
            self._config.timeout,
        )


async def _retry_async(coro_fn, max_retries: int, timeout: float):
    """Run async coroutine with retries and timeout."""
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await asyncio.wait_for(coro_fn(), timeout=timeout)
        except (TimeoutError, asyncio.TimeoutError) as e:
            last_err = e
            if attempt < max_retries:
                await asyncio.sleep(2**attempt)
        except Exception as e:
            last_err = e
            if attempt < max_retries and _is_retryable(e):
                await asyncio.sleep(2**attempt)
            else:
                raise
    if last_err:
        raise last_err
    raise RuntimeError("Unexpected retry loop exit")


def create_llm_client(
    preset: str,
    config: LLMConfig,
    *,
    anthropic_api_key: str | None = None,
    google_api_key: str | None = None,
    deepseek_api_key: str | None = None,
    openai_api_key: str | None = None,
) -> BaseLLMClient:
    """Factory: build a unified LLM client for the given preset."""
    if preset not in LLM_PRESETS:
        raise ValueError(
            f"preset must be one of {list(LLM_PRESETS.keys())}, got {preset!r}"
        )
    model_id = LLM_PRESETS[preset]

    if preset == "claude-haiku":
        return _AnthropicClient(model_id, config, api_key=anthropic_api_key)
    if preset == "gemini-flash":
        return _GeminiClient(model_id, config, api_key=google_api_key)
    if preset in ("deepseek_reasoner", "deepseek_chat"):
        return _DeepSeekClient(model_id, config, api_key=deepseek_api_key)
    if preset == "openai-chatgpt":
        return _OpenAIClient(model_id, config, api_key=openai_api_key)
    raise ValueError(f"Unknown preset: {preset!r}")
