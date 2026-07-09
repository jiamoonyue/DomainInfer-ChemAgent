"""Ollama Provider — local models via LiteLLM.

Design doc 5.2: Ollama as ultimate fallback (local model, no API cost).
"""

from app.providers.litellm_provider import LiteLLMProvider


class OllamaProvider(LiteLLMProvider):
    """Ollama-specific provider. Model format: 'ollama/qwen3:8b'."""

    def __init__(self, model: str = "qwen3:8b"):
        super().__init__(model=f"ollama/{model}")

    @property
    def provider_name(self) -> str:
        return "ollama"
