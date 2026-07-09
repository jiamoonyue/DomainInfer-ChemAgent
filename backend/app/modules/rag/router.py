"""RAG router — search, agentic search, ingestion, and chunk management."""

import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import GetDB
from app.core.config import PROJECT_ROOT
from app.modules.rag.service import RAGService
from app.modules.rag.schemas import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    AgenticSearchRequest,
    AgenticSearchResponse,
    ChunkInfo,
    NamespaceStats,
)

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, db: GetDB):
    """Hybrid search: BGE-M3 dense + BM25 sparse + RRF fusion."""
    t0 = time.time()
    svc = RAGService(db)
    results = await svc.search(req.query, req.namespace, req.top_k)
    return SearchResponse(
        results=[
            SearchResult(
                chunk_id=r.get("id", r.get("source", "")),
                content=r["content"][:300],
                source=r.get("source", "unknown"),
                score=r.get("score", 0),
                method=r.get("method", "unknown"),
            )
            for r in results
        ],
        query=req.query,
        latency_ms=round((time.time() - t0) * 1000, 1),
    )


@router.post("/agentic-search", response_model=AgenticSearchResponse)
async def agentic_search(req: AgenticSearchRequest, db: GetDB):
    """Agentic RAG: Query Rewriting → Retrieval → Relevance Scoring → Synthesis."""
    svc = RAGService(db)
    result = await svc.agentic_search(req.query, req.namespace, req.max_rounds)
    return AgenticSearchResponse(**result)


@router.post("/ingest/{namespace}")
async def ingest_namespace(namespace: str, db: GetDB):
    """Re-index all documents in a namespace directory."""
    knowledge_dir = PROJECT_ROOT / "knowledge" / namespace
    if not knowledge_dir.exists():
        raise HTTPException(404, f"Knowledge directory not found: {namespace}")

    svc = RAGService(db)
    results = await svc.ingest_directory(knowledge_dir, namespace)
    total = sum(results.values())
    await db.commit()
    return {"ok": True, "namespace": namespace, "files": len(results), "chunks": total, "details": results}


@router.get("/stats/{namespace}", response_model=NamespaceStats)
async def namespace_stats(namespace: str, db: GetDB):
    """Get document/chunk counts and last update time for a namespace."""
    svc = RAGService(db)
    stats = await svc.get_namespace_stats(namespace)
    return NamespaceStats(**stats)


@router.get("/chunks/{namespace}", response_model=list[ChunkInfo])
async def list_chunks(
    namespace: str,
    db: GetDB,
    limit: int = Query(default=50, ge=1, le=200),
):
    """List chunks in a namespace with metadata."""
    svc = RAGService(db)
    chunks = await svc.list_chunks(namespace, limit)
    return [ChunkInfo(**c) for c in chunks]


@router.get("/ping")
async def rag_ping():
    return {"module": "rag", "status": "active", "engine": "Hybrid+Dense+BM25+RRF+Agentic"}
