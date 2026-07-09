<div align="center">

# AgentForge

**Enterprise AI Agent Development Platform**

*Multi-Agent Orchestration · Agentic RAG · MCP Tool Protocol · Production-Grade Observability*

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136+-00a393?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-purple?style=flat-square)](/)
[![LiteLLM](https://img.shields.io/badge/LiteLLM-1.50+-orange?style=flat-square)](/)
[![React](https://img.shields.io/badge/React-19+-61dafb?style=flat-square&logo=react)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=flat-square&logo=postgresql)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-dc382d?style=flat-square&logo=redis)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ed?style=flat-square&logo=docker)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-31_passing-brightgreen?style=flat-square)](/)

</div>

---

## Overview

**AgentForge** is a production-ready, enterprise-grade AI Agent development platform. It provides a complete stack for building, deploying, and monitoring intelligent agents — from ReAct-based reasoning loops and multi-agent routing to hybrid retrieval-augmented generation (RAG), all wrapped in a modular monolith architecture deployable with a single `docker compose up`.

Originally built as a chemical engineering domain project (ChemAgent), AgentForge has been generalized into a domain-agnostic platform suitable for **customer support agents, research assistants, process automation, knowledge QA systems**, and more.

### Architecture

```
React Frontend (Vite + TypeScript + Tailwind)
        │ SSE streaming
        ▼
┌───────────────────────────────────────┐
│      FastAPI Backend (Modular Monolith) │
│                                        │
│  ┌──────┐ ┌──────────┐ ┌──────────┐   │
│  │ Auth │ │  Agent   │ │   RAG    │   │
│  │Module│ │  Engine   │ │  Module  │   │
│  └──┬───┘ └────┬─────┘ └────┬─────┘   │
│     │          │             │         │
│     └──────────┼─────────────┘         │
│                ▼                       │
│    ┌────────────────────────┐          │
│    │  Provider Layer        │          │
│    │  (LiteLLM + Circuit    │          │
│    │   Breaker Failover)    │          │
│    └────────────────────────┘          │
└─────────────────┬─────────────────────┘
                  │
       ┌──────────┴──────────┐
       │                      │
       ▼                      ▼
┌──────────────┐     ┌──────────────┐
│  PostgreSQL   │     │    Redis     │
│  (Persistence) │     │  (Cache/     │
│               │     │   Rate Limit) │
└──────────────┘     └──────────────┘
```

### Data Flow: One Complete Request

```
User → React UI → Nginx → FastAPI → AuthMiddleware (JWT) → RateLimitMiddleware (Redis)
  → Agent Engine → Classify Node → Route to Best Agent → RAG Context Injection
  → Think Node (LiteLLM) → Execute Tool? → Yes → Tool → Back to Think
  → Respond → SSE Stream → React UI
  ↓
  OpenTelemetry traces every step → Jaeger
  Prometheus records metrics
```

---

## Key Features

### 🤖 Multi-Agent Orchestration (LangGraph)
- **ReAct Loop**: Reasoning + Acting cycle — the agent thinks, optionally calls tools, observes results, and responds
- **StateGraph Pipeline**: `classify → think → [execute_tool → think → ...] → respond`
- **Intelligent Routing**: Automatic agent selection by domain (calculation, safety, knowledge, process)
- **Streaming**: Real-time SSE (Server-Sent Events) for token-by-token output

### 🔌 Provider Layer with Circuit Breaker
- **Unified API**: Single interface for 100+ LLMs via LiteLLM (`provider/model_name` format)
- **Circuit Breaker Failover**: Primary → Fallback 1 → Fallback 2 chain, auto-cooldown on failure
- **Multi-Provider**: DeepSeek, OpenAI, Anthropic, Ollama — all pluggable
- **Token Tracking**: Cost accounting per conversation

### 📚 Agentic RAG (Hybrid Search)
- **Query Rewriting**: LLM rewrites user query for better retrieval
- **Hybrid Search**: BGE-M3 dense embeddings + BM25 sparse retrieval + RRF fusion ranking
- **Corrective Retrieval**: Relevance scoring triggers re-retrieval when needed
- **Chunk Lifecycle**: SHA-256 content hashing, `stable_id` version tracking, incremental updates
- **Namespace Isolation**: Separate knowledge bases per domain (chem, legal, medical, ...)

### 🔧 MCP Tool Protocol
- **JSON-RPC Standard**: Tools discovery (`tools/list`) and execution (`tools/call`)
- **10 Built-in Tools**: 6 domain tools (molecular weight, unit conversion, etc.) + 4 external APIs (PubChem, NIST, arXiv)
- **Extension-Ready**: Register new tools via `TOOL_DEFINITIONS` — no additional boilerplate

### 🔐 Enterprise Security
- **JWT Dual Token**: 15-minute access token + 7-day refresh token
- **API Key Support**: Programmatic access with API key management
- **RBAC**: Three roles — `admin`, `user`, `viewer`
- **Global Auth Middleware**: All `/api/*` endpoints protected by default
- **Redis Rate Limiting**: Configurable per-user quota (default: 20 req/min)

### 📊 Production Observability
- **OpenTelemetry + Jaeger**: Distributed tracing for every Agent step
- **Prometheus Metrics**: Request counts, latency histograms, token usage
- **Dashboard**: Jaeger UI at port 16686 for trace visualization

### 💻 Modern Frontend
- **React 19 + TypeScript + Vite + Tailwind CSS**
- **Real-time SSE Streaming**: Token-by-token display of agent responses
- **Conversation Management**: Sidebar history with auto-titling
- **Tool Call Visualization**: Expandable cards showing tool invocations

---

## Tech Stack

| Category | Technology |
|----------|-----------|
| **Backend Framework** | FastAPI (async, auto-OpenAPI, SSE streaming) |
| **Agent Framework** | LangGraph StateGraph (ReAct loop) |
| **LLM Gateway** | LiteLLM (100+ models via unified API) |
| **Database** | PostgreSQL 15 + SQLAlchemy 2.0 (async) |
| **Cache/Queue** | Redis 7 (rate limiting, caching, distributed locks) |
| **Vector Search** | BGE-M3 embeddings + BM25 (hybrid search) |
| **Auth** | JWT (access + refresh tokens), bcrypt, RBAC |
| **Observability** | OpenTelemetry, Jaeger, Prometheus |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS |
| **Deployment** | Docker Compose (5 services) |
| **Testing** | pytest, pytest-asyncio, httpx |
| **Migration** | Alembic |

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)
- Python 3.10+ (for local development)

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/jiamoonyue/DomainInfer-ChemAgent.git
cd DomainInfer-ChemAgent

# 2. Configure environment
cp .env.example .env
# Edit .env: set your DEEPSEEK_API_KEY, SECRET_KEY, etc.

# 3. Start all services
docker compose up -d

# 4. Verify deployment
curl http://localhost/api/status
# {"status":"running","version":"0.1.0","database":"configured","redis":"configured",...}

# 5. Open the app
# Frontend: http://localhost
# API Docs: http://localhost/docs
# Jaeger UI: http://localhost:16686
```

### Option 2: Local Development

```bash
# 1. Start infrastructure (PostgreSQL + Redis + Jaeger)
docker compose up -d postgres redis jaeger

# 2. Set up Python environment
cd backend
pip install -e ../[dev]

# 3. Run database migrations
alembic upgrade head

# 4. Start the backend
uvicorn app.main:app --reload --port 8000

# 5. In another terminal, start the frontend
cd frontend
npm install
npm run dev
```

---

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_HOST` | `0.0.0.0` | Server bind address |
| `SERVER_PORT` | `8000` | Server port |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `DEEPSEEK_API_KEY` | — | DeepSeek API key |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | Model name |
| `USE_API` | `true` | Enable API mode |
| `SECRET_KEY` | — | JWT signing secret (min 32 chars) |
| `ADMIN_EMAIL` | `admin@agentforge.local` | Auto-created admin |
| `ADMIN_PASSWORD` | `admin123` | Admin password |
| `RATE_LIMIT_PER_MINUTE` | `20` | Requests per minute per user |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://jaeger:4317` | OpenTelemetry endpoint |

---

## Project Structure

```
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── core/              # Config, DB, Redis, security, middleware
│   │   ├── modules/
│   │   │   ├── auth/          # User management, JWT, RBAC, API keys
│   │   │   ├── agents/        # LangGraph engine, ReAct loop, multi-agent routing
│   │   │   ├── rag/           # Hybrid search, Agentic RAG, chunk lifecycle
│   │   │   ├── tools/         # MCP tool registry, 10 tools, audit logs
│   │   │   ├── knowledge/     # Document upload, namespace management
│   │   │   ├── conversations/ # Chat history, message CRUD
│   │   │   └── observability/ # Token cost, usage analytics
│   │   ├── providers/         # LLM adapters (LiteLLM, OpenAI, Anthropic, Ollama, DeepSeek, CircuitBreaker)
│   │   └── mcp/               # MCP JSON-RPC server
│   ├── tests/                 # 31 tests (unit + integration)
│   ├── migrations/            # Alembic database migrations
│   └── alembic.ini
├── frontend/                   # React + TypeScript + Vite + Tailwind
│   └── src/
│       ├── App.tsx            # Main chat UI with SSE streaming
│       ├── main.tsx           # Entry point
│       └── index.css          # Tailwind imports
├── agents/                     # Agent YAML configuration files
├── knowledge/                  # Knowledge base source files
├── prompts/                    # Jinja2 prompt templates
├── nginx/                      # Nginx configuration (SSE proxy)
├── docs/                       # Architecture documentation
├── docker-compose.yml          # 5-service Docker orchestration
├── Dockerfile                  # Backend container image
└── pyproject.toml              # Python dependencies & metadata
```

---

## API Overview

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Liveness probe |
| `/api/status` | GET | No | Server status |
| `/api/auth/register` | POST | No | User registration |
| `/api/auth/login` | POST | No | Login (returns JWT) |
| `/api/auth/refresh` | POST | No | Refresh access token |
| `/api/auth/me` | GET | JWT | Current user info |
| `/api/chat` | POST | JWT | Chat with Agent (SSE stream) |
| `/api/agents` | GET | No | List configured agents |
| `/api/tools` | GET | No | List available tools (MCP) |
| `/api/tools/call` | POST | No | Execute a tool (MCP) |
| `/api/search` | POST | JWT | Hybrid search |
| `/api/agentic-search` | POST | JWT | Agentic RAG search |
| `/api/ingest/{namespace}` | POST | JWT | Ingest documents |
| `/api/knowledge/namespaces` | GET | No | List knowledge namespaces |
| `/api/conversations` | GET | JWT | List conversations |
| `/api/observability/overview` | GET | JWT | Usage overview |
| `/metrics` | GET | No | Prometheus metrics |

Full interactive API documentation at `http://localhost/docs` (Swagger UI).

---

## Testing

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific test modules
pytest tests/test_tools.py -v    # 14 tool tests
pytest tests/test_security.py -v # 5 security tests
pytest tests/test_integration.py -v # 12 integration tests

# With coverage
pip install pytest-cov
pytest tests/ --cov=app -v
```

**31 tests total**: 19 unit tests (tools & security) + 12 integration tests (API endpoints).

---

## Agent Configuration

Agents are defined as YAML files in the `agents/` directory:

```yaml
name: chem-calculator
display_name: Chemical Calculator
description: Expert in chemical engineering calculations
type: calculation
model: deepseek/deepseek-chat
temperature: 0.3
system_prompt: |
  You are a chemical engineering calculation expert.
  Use tools for precise calculations and show your work.
```

Built-in agents:
- **Chemical Calculator** (`calculation`) — stoichiometry, gas laws, unit conversion
- **Safety Analyst** (`safety`) — chemical safety, MSDS interpretation
- **Domain Knowledge** (`knowledge`) — RAG-augmented knowledge base QA
- **Process Engineer** (`process`) — process design, equipment sizing

---

## Services (Docker)

| Service | Port | Description |
|---------|------|-------------|
| `nginx` | `80` | Reverse proxy with SSE buffering |
| `backend` | `8000` | FastAPI application |
| `postgres` | `5432` | PostgreSQL 15 database |
| `redis` | `6379` | Redis 7 cache & rate limiter |
| `jaeger` | `16686` | Jaeger tracing UI |

---

## Extending AgentForge

### Add a New Tool

```python
from app.modules.tools.engine import TOOL_DEFINITIONS, execute_tool

def my_custom_tool(param1: str, param2: int) -> str:
    """Do something useful."""
    return f"Result: {param1 * param2}"

TOOL_DEFINITIONS["my_custom_tool"] = {
    "name": "my_custom_tool",
    "description": "Description of what my tool does",
    "input_schema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "First parameter"},
            "param2": {"type": "integer", "description": "Second parameter"},
        },
        "required": ["param1", "param2"],
    },
    "fn": my_custom_tool,
}
```

### Add a New Provider

Create a class inheriting from `BaseLLMProvider` and implement `chat()` and `chat_stream()`.

### Add a New Agent

Create a YAML file in `agents/` and the routing system will automatically pick it up.

---

## License

MIT

---

## Acknowledgements

Built with [FastAPI](https://fastapi.tiangolo.com/), [LangGraph](https://langchain-ai.github.io/langgraph/), [LiteLLM](https://litellm.vercel.app/), and the open-source community.

---

*AgentForge — From prototype to production, one agent at a time.*
