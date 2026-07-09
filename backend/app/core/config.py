"""AgentForge Configuration — Pydantic Settings loaded from .env"""

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


# Project root: AgentForge/ (two levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """All application settings, loaded from .env / environment."""

    # ---- Server ----
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # ---- Database ----
    DATABASE_URL: str = "postgresql+asyncpg://agentforge:agentforge@localhost:5432/agentforge"
    DATABASE_URL_SYNC: str = "postgresql://agentforge:agentforge@localhost:5432/agentforge"

    # ---- Redis ----
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---- LLM API ----
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    USE_API: bool = True

    # ---- Auth ----
    SECRET_KEY: str = "change-me-to-a-random-secret-at-least-32-chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---- Rate Limiting ----
    RATE_LIMIT_PER_MINUTE: int = 20

    # ---- Admin bootstrap ----
    ADMIN_EMAIL: str = "admin@agentforge.local"
    ADMIN_PASSWORD: str = "admin123"

    # ---- Observability ----
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    ENABLE_METRICS: bool = True

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()


settings = get_settings()
