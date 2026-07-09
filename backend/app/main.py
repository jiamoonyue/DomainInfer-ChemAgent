"""AgentForge — Enterprise AI Agent Development Platform.

Design doc architecture:
  React Frontend → FastAPI Backend → Provider Adapter (LiteLLM + CB)
                                     → PostgreSQL + Redis
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

# Prometheus — design doc 5.7-B (optional: app works without it)
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = Histogram = None  # type: ignore
    generate_latest = CONTENT_TYPE_LATEST = ""  # type: ignore

from app.core.config import settings, PROJECT_ROOT
from app.core.exceptions import register_exception_handlers
from app.core.middleware import AuthMiddleware, RateLimitMiddleware, PUBLIC_PATHS
from app.core.otel import setup_otel, shutdown_otel

# ---- Prometheus Metrics (Design doc 5.7-B) ----
if PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter("agentforge_requests_total", "Total requests", ["method", "endpoint"])
    REQUEST_LATENCY = Histogram("agentforge_request_duration_seconds", "Request latency", ["method", "endpoint"])
    TOKEN_USAGE = Counter("agentforge_token_usage_total", "Total tokens used", ["type"])
    TOOL_CALLS = Counter("agentforge_tool_calls_total", "Total tool calls")
else:
    REQUEST_COUNT = None  # type: ignore
    REQUEST_LATENCY = None  # type: ignore
    TOKEN_USAGE = None  # type: ignore
    TOOL_CALLS = None  # type: ignore


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    print(f"[AgentForge] Starting server on {settings.SERVER_HOST}:{settings.SERVER_PORT}")
    print(f"[AgentForge] USE_API={settings.USE_API}, MODEL={settings.DEEPSEEK_MODEL}")
    print("[AgentForge] DB and Redis connect lazily on first request")

    yield

    setup_otel(app)
    print("[AgentForge] Shutting down...")
    shutdown_otel()


app = FastAPI(
    title="AgentForge",
    description="Enterprise AI Agent Development Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware stack (order matters: outer -> inner)
# 1. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 2. Rate Limiting (Redis-based, 20 req/min per user — Design doc 6.1)
app.add_middleware(RateLimitMiddleware)
# 3. Auth Enforcement (Design doc 6.1: all /api/* need Authorization)
app.add_middleware(AuthMiddleware)

register_exception_handlers(app)


# ---- Prometheus /metrics endpoint (Design doc 5.7-B) ----


@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics endpoint (Design doc 5.7-B)."""
    if not PROMETHEUS_AVAILABLE:
        return Response(content="Prometheus client not installed\n", media_type="text/plain")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---- Health & Status ----

@app.get("/health")
async def health():
    """Kubernetes-style liveness probe."""
    return {"status": "ok"}


@app.get("/api/status")
async def status():
    """Detailed server status (no live DB checks — see /api/observability/overview)."""
    return {
        "status": "running",
        "version": "0.1.0",
        "database": "configured",
        "redis": "configured",
        "use_api": settings.USE_API,
        "model": settings.DEEPSEEK_MODEL if settings.USE_API else "local",
    }


# ---- Real Module Routers ----

from app.modules.auth.router import router as auth_router
from app.modules.agents.router import router as agents_router
from app.modules.rag.router import router as rag_router
from app.modules.conversations.router import router as conversations_router
from app.modules.observability.router import router as observability_router
from app.modules.tools.router import router as tools_router
from app.modules.knowledge.router import router as knowledge_router

app.include_router(auth_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(rag_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")
app.include_router(observability_router, prefix="/api")
app.include_router(tools_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
