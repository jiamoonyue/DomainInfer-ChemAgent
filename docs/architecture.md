# AgentForge Architecture

## Overview

AgentForge is an enterprise-grade AI Agent development platform. It provides
Multi-Agent orchestration, Agentic RAG, MCP-standard tool protocol, multi-LLM
provider support with circuit breaker fallback, and production-grade observability.

Built as a modular monolith with FastAPI, PostgreSQL, Redis, and LangGraph.

## Architecture Diagram

```
React Frontend (Vite + TypeScript + Tailwind)
        │ SSE streaming
        ▼
┌───────────────────────────────────┐
│  FastAPI Backend (Module Monolith) │
│                                    │
│  ┌──────┐ ┌────────┐ ┌──────┐     │
│  │ Auth │ │ Agent  │ │ RAG  │     │
│  │Module│ │ Engine │ │Module│     │
│  └──┬───┘ └───┬────┘ └──┬───┘     │
│     │          │          │        │
│     └──────────┼──────────┘        │
│                ▼                   │
│     ┌──────────────────┐           │
│     │ Provider Adapter  │           │
│     │ (LiteLLM + CB)    │           │
│     └──────────────────┘           │
│                │                   │
└────────────────┼───────────────────┘
                 ▼
      ┌──────────┴──────────┐
      │                      │
      ▼                      ▼
┌──────────┐          ┌──────────┐
│PostgreSQL│          │  Redis   │
└──────────┘          └──────────┘
```

## Data Flow: A Complete Request

```
1. User sends question via React UI
2. Nginx proxies to FastAPI backend
3. AuthMiddleware validates JWT/API key
4. RateLimitMiddleware checks Redis quota (20 req/min)
5. Agent Engine receives message
6. Classify node routes to best agent (calculation/safety/knowledge/process)
7. RAG context is retrieved and injected
8. Think node: LLM reasons via LiteLLM
9. If tool call required: execute_tool node runs tool
10. Tool result goes back to think node
11. Final answer streams via SSE to frontend
12. OpenTelemetry traces every step -> Jaeger
```

## Module Boundaries

| Module | Responsibility | Key Files |
|--------|---------------|-----------|
| auth | User management, JWT, RBAC | `modules/auth/` |
| agents | LangGraph engine, ReAct loop, Multi-Agent routing | `modules/agents/service.py` |
| rag | Agentic RAG, hybrid search, chunk lifecycle | `modules/rag/service.py` |
| tools | MCP tool registry, 10 tools (6 local + 4 API), audit | `modules/tools/engine.py` |
| knowledge | Document upload, namespace isolation | `modules/knowledge/router.py` |
| conversations | Chat CRUD, message history, summaries | `modules/conversations/router.py` |
| observability | Token cost tracking, daily reports, metrics | `modules/observability/router.py` |
| providers | LLM abstraction: LiteLLM, OpenAI, Anthropic, Ollama, CircuitBreaker | `providers/` |
| mcp | MCP JSON-RPC server, tool registry | `mcp/` |

## Provider Strategy

```
CircuitBreakerProvider
  ├── LiteLLMProvider("deepseek/deepseek-chat")  [primary]
  ├── LiteLLMProvider("anthropic/claude-haiku")  [fallback 1]
  └── LiteLLMProvider("ollama/qwen3:8b")         [fallback 2 — local, zero cost]
```

## Database Schema

11 tables: users, api_keys, conversations, messages, documents, chunks,
embedding_versions, tool_definitions, tool_call_logs, token_usage_logs,
prompt_configs.

All use UUID primary keys, created_at/updated_at timestamps, and proper
foreign key constraints.

## Deployment

```bash
docker compose up  # Starts all 5 services
```

- Backend: FastAPI on :8000
- Frontend: Nginx-served React on :80
- PostgreSQL: port 5432
- Redis: port 6379
- Jaeger UI: port 16686 (OpenTelemetry traces)

## Testing

```bash
cd backend && pytest tests/ -v
```

19 unit tests (tools + security) + 12 integration tests (API endpoints).
