"""AgentForge — Enterprise AI Agent Development Platform."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings, PROJECT_ROOT
from app.core.exceptions import register_exception_handlers
from app.core.otel import setup_otel, shutdown_otel


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    print(f"[AgentForge] Starting server on {settings.SERVER_HOST}:{settings.SERVER_PORT}")
    print(f"[AgentForge] USE_API={settings.USE_API}")
    print("[AgentForge] DB and Redis will connect on first request")

    # DB/Redis init happens lazily on first request to avoid blocking startup

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)


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
