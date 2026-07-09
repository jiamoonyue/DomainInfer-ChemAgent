"""OpenAI Provider — via LiteLLM.

Design doc 5.2 Provider Adapter: "OpenAI / Anthropic / Ollama 统一适配，一行切换"
"""

from app.providers.litellm_provider import LiteLLMProvider


class OpenAIProvider(LiteLLMProvider):
    """OpenAI-specific provider. Model format: 'openai/gpt-4o-mini'."""

    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__(model=f"openai/{model}")

    @property
    def provider_name(self) -> str:
        return "openai"
