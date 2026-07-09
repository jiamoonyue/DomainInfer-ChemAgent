"""RAG models — Document, Chunk, EmbeddingVersion."""

import uuid
from datetime import datetime

from sqlalchemy import Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import BaseModel


class Document(BaseModel):
    __tablename__ = "documents"

    namespace: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(128), nullable=False)  # SHA256
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | indexing | error

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Chunk(BaseModel):
    __tablename__ = "chunks"

    stable_id: Mapped[str] = mapped_column(String(256), unique=True, nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)  # SHA256
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | inactive | deleted
    metadata_: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="chunks")
    embeddings: Mapped[list["EmbeddingVersion"]] = relationship(back_populates="chunk", cascade="all, delete-orphan")


class EmbeddingVersion(BaseModel):
    __tablename__ = "embedding_versions"

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    vector_dim: Mapped[int] = mapped_column(Integer, nullable=False)

    chunk: Mapped["Chunk"] = relationship(back_populates="embeddings")
