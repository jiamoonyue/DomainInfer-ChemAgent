"""Alembic environment configuration — loads all SQLAlchemy models."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.core.config import settings
from app.core.database import Base  # noqa: F401

# Import all models so Alembic detects them
from app.modules.auth.models import User, ApiKey  # noqa: F401
from app.modules.conversations.models import Conversation, Message  # noqa: F401
from app.modules.rag.models import Document, Chunk, EmbeddingVersion  # noqa: F401
from app.modules.tools.models import ToolDefinition, ToolCallLog  # noqa: F401
from app.modules.observability.models import TokenUsageLog  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = settings.DATABASE_URL_SYNC
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
