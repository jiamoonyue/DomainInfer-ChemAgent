"""RAG schemas — Pydantic models for search, ingest, and agentic RAG."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4096)
    namespace: str = "chem"
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    chunk_id: str
    content: str
    source: str
    score: float
    method: str  # dense | bm25 | keyword_boosted


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
    latency_ms: float


class AgenticSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4096)
    namespace: str = "chem"
    max_rounds: int = Field(default=3, ge=1, le=5)


class AgenticSearchResponse(BaseModel):
    final_answer: str
    sub_queries: list[str] = []
    sources_used: list[str] = []
    rounds: int
    latency_ms: float


class ChunkInfo(BaseModel):
    id: UUID
    stable_id: str
    version: int
    status: str
    content_preview: str = Field(default="", max_length=200)
    document_filename: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentInfo(BaseModel):
    id: UUID
    namespace: str
    filename: str
    chunk_count: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class NamespaceStats(BaseModel):
    namespace: str
    document_count: int
    chunk_count: int
    last_updated: datetime | None
