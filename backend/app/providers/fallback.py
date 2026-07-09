"""Circuit Breaker — 设计文档 5.2 的熔断降级实现。

Design doc:
  self.primary = LiteLLM(model="gpt-4o-mini")      # 主模型(API)
  self.fallback1 = LiteLLM(model="claude-haiku")    # 备选1(API)
  self.fallback2 = LiteLLM(model="ollama/qwen3")    # 备选2(本地)
"""

import time
from typing import AsyncIterator

from app.providers.base import BaseLLMProvider, LLMResponse, LLMStreamChunk


class CircuitBreakerProvider(BaseLLMProvider):
    """Try providers in order. On failure, fall through to the next.

    On timeout/error, record failure. If failures > threshold within cooldown
    window, skip that provider (circuit open). On success, resets failures.
    """

    def __init__(
        self,
        providers: list[BaseLLMProvider],
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
    ):
        self._providers = providers
        self._threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._failures: dict[str, list[float]] = {}

    @property
    def provider_name(self) -> str:
        return "+".join(p.provider_name for p in self._providers)

    def _is_open(self, name: str) -> bool:
        timestamps = self._failures.get(name, [])
        now = time.time()
        recent = [t for t in timestamps if now - t < self._cooldown]
        self._failures[name] = recent
        return len(recent) >= self._threshold

    def _record_failure(self, name: str):
        self._failures.setdefault(name, []).append(time.time())

    def _record_success(self, name: str):
        self._failures.pop(name, None)

    async def chat(self, messages, temperature=0.7, max_tokens=2048) -> LLMResponse:
        last_error = None
        for provider in self._providers:
            if self._is_open(provider.provider_name):
                continue
            try:
                resp = await provider.chat(messages, temperature, max_tokens)
                self._record_success(provider.provider_name)
                return resp
            except Exception as e:
                self._record_failure(provider.provider_name)
                last_error = e

        raise RuntimeError(f"All providers failed. Last: {last_error}")

    async def chat_stream(
        self, messages, temperature=0.7, max_tokens=2048
    ) -> AsyncIterator[LLMStreamChunk]:
        last_error = None
        for provider in self._providers:
            if self._is_open(provider.provider_name):
                continue
            try:
                stream = provider.chat_stream(messages, temperature, max_tokens)
                async for chunk in stream:
                    yield chunk
                self._record_success(provider.provider_name)
                return
            except Exception as e:
                self._record_failure(provider.provider_name)
                last_error = e

        raise RuntimeError(f"All providers failed streaming. Last: {last_error}")
