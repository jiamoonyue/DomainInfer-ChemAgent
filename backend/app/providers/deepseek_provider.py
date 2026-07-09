"""DeepSeek Provider — wraps DeepSeekClient as a BaseLLMProvider."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.providers.base import BaseLLMProvider, LLMResponse, LLMStreamChunk
from app.providers.deepseek_client import get_deepseek_client

_executor = ThreadPoolExecutor(max_workers=1)


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API provider (async wrapper over sync client)."""

    def __init__(self, model: str | None = None):
        self._client = get_deepseek_client()
        self._model = model or self._client.model

    @property
    def provider_name(self) -> str:
        return "deepseek"

    async def chat(self, messages, temperature=0.7, max_tokens=2048) -> LLMResponse:
        loop = asyncio.get_running_loop()

        def _call():
            resp = self._client.create_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )
            choice = resp["choices"][0]
            usage = resp.get("usage", {})
            return LLMResponse(
                content=choice["message"]["content"] or "",
                model=self._model,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                provider=self.provider_name,
            )

        return await loop.run_in_executor(_executor, _call)

    async def chat_stream(self, messages, temperature=0.7, max_tokens=2048):
        loop = asyncio.get_running_loop()

        # Run sync stream in thread, collect all chunks first
        def _collect():
            stream = self._client.create_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            results = []
            for chunk in stream:
                content = chunk["choices"][0]["delta"].get("content", "")
                if content:
                    results.append(content)
            return results

        chunks = await loop.run_in_executor(_executor, _collect)
        for content in chunks:
            yield LLMStreamChunk(content=content)
