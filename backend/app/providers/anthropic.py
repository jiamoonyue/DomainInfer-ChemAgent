"""Anthropic Provider — via LiteLLM.

Design doc 5.2: Anthropic as fallback in CircuitBreaker chain.
"""

from app.providers.litellm_provider import LiteLLMProvider


class AnthropicProvider(LiteLLMProvider):
    """Anthropic-specific provider. Model format: 'anthropic/claude-haiku-4-5-20251001'."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        super().__init__(model=f"anthropic/{model}")

    @property
    def provider_name(self) -> str:
        return "anthropic"
