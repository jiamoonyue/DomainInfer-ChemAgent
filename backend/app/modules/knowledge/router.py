"""Knowledge Base router — document upload, namespace management."""

import hashlib
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import GetDB, CurrentAdmin
from app.core.config import PROJECT_ROOT
from app.modules.rag.models import Document, Chunk
from app.modules.rag.service import _chunk_text

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"


class NamespaceInfo(BaseModel):
    namespace: str
    document_count: int
    chunk_count: int

    model_config = {"from_attributes": True}


@router.get("/ping")
async def knowledge_ping():
    return {"module": "knowledge", "status": "active"}


@router.get("/namespaces", response_model=list[str])
async def list_namespaces():
    """List available knowledge namespaces (directories under knowledge/)."""
    if not KNOWLEDGE_DIR.exists():
        return []
    return sorted([
        d.name for d in KNOWLEDGE_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])


@router.get("/{namespace}", response_model=NamespaceInfo)
async def namespace_info(namespace: str):
    """Get document count for a namespace (filesystem-based, no DB)."""
    ns_dir = KNOWLEDGE_DIR / namespace
    files = list(ns_dir.rglob("*")) if ns_dir.exists() else []
    doc_count = sum(1 for f in files if f.is_file() and f.suffix in ('.md', '.txt'))
    return NamespaceInfo(namespace=namespace, document_count=doc_count, chunk_count=0)


@router.post("/{namespace}/upload")
async def upload_document(namespace: str, file: UploadFile = File(...), db: GetDB = None):
    """Upload a document to a namespace. Triggers indexing in RAG."""
    ns_dir = KNOWLEDGE_DIR / namespace
    ns_dir.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    text = content.decode("utf-8")
    file_hash = hashlib.sha256(text.encode()).hexdigest()

    # Save file
    filepath = ns_dir / file.filename
    filepath.write_text(text, encoding="utf-8")

    # Index into DB
    from app.modules.rag.service import RAGService
    svc = RAGService(db)

    # Check existing
    existing = await db.scalar(
        select(Document).where(
            Document.namespace == namespace,
            Document.filename == file.filename,
        )
    )

    if existing and existing.file_hash == file_hash:
        return {"ok": True, "filename": file.filename, "namespace": namespace, "chunks": 0, "status": "unchanged"}

    if existing:
        existing.file_hash = file_hash
        existing.status = "indexing"
        await db.flush()
        doc = existing
    else:
        doc = Document(
            namespace=namespace,
            filename=file.filename,
            file_hash=file_hash,
            file_path=str(filepath),
            status="indexing",
        )
        db.add(doc)
        await db.flush()

    # Chunk
    chunks = _chunk_text(text, file.filename)
    for c in chunks:
        chunk = Chunk(
            stable_id=f"{namespace}:{file.filename}:v1:{c['index']:04d}",
            document_id=doc.id,
            version=1,
            content=c["text"],
            content_hash=hashlib.sha256(c["text"].encode()).hexdigest(),
            metadata_={"source": c["source"], "index": c["index"]},
        )
        db.add(chunk)

    doc.chunk_count = len(chunks)
    doc.status = "active"
    await db.flush()
    await db.commit()

    return {"ok": True, "filename": file.filename, "namespace": namespace, "chunks": len(chunks), "status": "indexed"}


@router.delete("/{namespace}/documents/{doc_id}", status_code=204)
async def delete_document(namespace: str, doc_id: str, db: GetDB):
    """Soft-delete a document and its chunks."""
    from uuid import UUID
    doc = await db.scalar(
        select(Document).where(Document.id == UUID(doc_id), Document.namespace == namespace)
    )
    if not doc:
        raise HTTPException(404, "Document not found")
    doc.status = "deleted"
    await db.execute(
        select(Chunk).where(Chunk.document_id == doc.id)
    )
    # Mark chunks deleted
    from sqlalchemy import update
    await db.execute(
        update(Chunk).where(Chunk.document_id == doc.id).values(status="deleted")
    )
    await db.flush()
    await db.commit()
