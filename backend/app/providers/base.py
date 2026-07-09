"""Abstract LLM Provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class LLMResponse:
    """Normalized LLM response across all providers."""
    content: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = "stop"
    provider: str = "unknown"


@dataclass
class LLMStreamChunk:
    """A single streaming token chunk."""
    content: str
    finish_reason: str | None = None


class BaseLLMProvider(ABC):
    """All LLM providers implement this interface."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Non-streaming chat completion."""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Iterator[LLMStreamChunk]:
        """Streaming chat completion — yields chunks."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name for auditing."""
        ...
