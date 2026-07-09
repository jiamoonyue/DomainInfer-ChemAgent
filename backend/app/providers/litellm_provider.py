"""LiteLLM Provider — wraps 100+ models behind a single interface.

Design doc 5.2: "用 LiteLLM 统一接口，一行配置切换模型"
"""

from typing import AsyncIterator

import litellm

from app.core.config import settings
from app.providers.base import BaseLLMProvider, LLMResponse, LLMStreamChunk


class LiteLLMProvider(BaseLLMProvider):
    """LiteLLM-based provider. Supports OpenAI, Anthropic, DeepSeek, Ollama, etc.

    Model format: "deepseek/deepseek-v4-flash", "openai/gpt-4o-mini",
                  "anthropic/claude-haiku-4-5-20251001", "ollama/qwen3:8b"
    """

    def __init__(self, model: str | None = None):
        model_str = model or settings.DEEPSEEK_MODEL
        # LiteLLM uses provider/model format; only add prefix if not already present
        if "/" not in model_str:
            model_str = f"deepseek/{model_str}"
        self._model = model_str

        if settings.DEEPSEEK_API_KEY:
            litellm.api_key = settings.DEEPSEEK_API_KEY

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return f"litellm({self._model})"

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Non-streaming chat via LiteLLM."""
        response = await litellm.acompletion(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=settings.DEEPSEEK_API_KEY,
        )
        choice = response.choices[0]
        usage = response.usage
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model or self._model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            finish_reason=choice.finish_reason or "stop",
            provider=self.provider_name,
        )

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Streaming chat via LiteLLM."""
        response = await litellm.acompletion(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            api_key=settings.DEEPSEEK_API_KEY,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta
            content = delta.content if delta.content is not None else ""
            if content:
                yield LLMStreamChunk(
                    content=content,
                    finish_reason=chunk.choices[0].finish_reason,
                )
