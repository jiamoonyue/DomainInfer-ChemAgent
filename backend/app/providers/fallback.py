"""Circuit-breaker fallback LLM provider — chains multiple providers."""

import time

from app.providers.base import BaseLLMProvider, LLMResponse, LLMStreamChunk


class CircuitBreakerProvider(BaseLLMProvider):
    """Try providers in order. On failure, fall through to the next.

    On success, reset failure count for the provider that succeeded.
    On timeout/error, increment failure count. If count > threshold, skip provider.
    """

    def __init__(
        self,
        providers: list[BaseLLMProvider],
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
        timeout_seconds: float = 60.0,
    ):
        self._providers = providers
        self._failure_threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._timeout = timeout_seconds
        self._failures: dict[str, list[float]] = {}  # provider_name -> [timestamps]

    @property
    def provider_name(self) -> str:
        return f"circuit_breaker({'+'.join(p.provider_name for p in self._providers)})"

    def _is_open(self, name: str) -> bool:
        """Check if circuit is open for this provider."""
        timestamps = self._failures.get(name, [])
        now = time.time()
        # Drop expired failures
        recent = [t for t in timestamps if now - t < self._cooldown]
        self._failures[name] = recent
        return len(recent) >= self._failure_threshold

    def _record_failure(self, name: str):
        """Record a failure timestamp."""
        self._failures.setdefault(name, []).append(time.time())

    def _record_success(self, name: str):
        """Reset failures on success."""
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
                continue

        raise RuntimeError(
            f"All providers failed. Last error: {last_error}"
        )

    async def chat_stream(self, messages, temperature=0.7, max_tokens=2048):
        last_error = None
        for provider in self._providers:
            if self._is_open(provider.provider_name):
                continue

            try:
                async for chunk in provider.chat_stream(messages, temperature, max_tokens):
                    yield chunk
                self._record_success(provider.provider_name)
                return
            except Exception as e:
                self._record_failure(provider.provider_name)
                last_error = e
                continue

        raise RuntimeError(
            f"All providers failed streaming. Last error: {last_error}"
        )
