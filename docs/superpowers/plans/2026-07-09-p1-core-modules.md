# P1: Auth + Agent Engine + Agentic RAG — Implementation Plan

> **Goal:** Implement user authentication, LangGraph-based Agent Engine with circuit-breaker fallback, and Agentic RAG pipeline.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, LangGraph, LiteLLM, BGE-M3, ChromaDB, JWT

## Global Constraints
- Python 3.13, FastAPI 0.136, SQLAlchemy 2.0 async
- PostgreSQL via Docker (standalone for dev), Redis via Docker
- All config via Pydantic Settings from `.env`
- Each module: `router.py` + `service.py` + `models.py` + `schemas.py`
- TDD: tests before implementation
- Commit after each module

---

### Module A: Alembic + Database Foundation

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/app/core/base_model.py` (shared base with UUID, timestamps)

### Module B: Auth Module

**Files:**
- Create: `backend/app/modules/auth/models.py` — User, ApiKey SQLAlchemy models
- Create: `backend/app/modules/auth/schemas.py` — Pydantic request/response
- Create: `backend/app/modules/auth/service.py` — register, login, token management
- Create: `backend/app/modules/auth/router.py` — API endpoints
- Create: `backend/app/core/deps.py` — get_current_user dependency

### Module C: Agent Engine

**Files:**
- Create: `backend/app/modules/agents/models.py` — AgentConfig model
- Create: `backend/app/modules/agents/schemas.py`
- Create: `backend/app/modules/agents/service.py` — LangGraph ReAct loop + LiteLLM + fallback
- Create: `backend/app/modules/agents/router.py` — POST /agents/chat (SSE streaming)
- Create: `backend/app/providers/base.py` — abstract LLM provider
- Create: `backend/app/providers/litellm_provider.py` — LiteLLM wrapper
- Create: `backend/app/providers/fallback.py` — CircuitBreakerLLM

### Module D: Agentic RAG

**Files:**
- Create: `backend/app/modules/rag/models.py` — Document, Chunk, EmbeddingVersion
- Create: `backend/app/modules/rag/schemas.py`
- Create: `backend/app/modules/rag/service.py` — AgenticRAG pipeline
- Create: `backend/app/modules/rag/router.py` — search, ingest, agentic-search
---
