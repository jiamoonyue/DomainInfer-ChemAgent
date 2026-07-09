"""AgentForge — Enterprise AI Agent Development Platform."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings, PROJECT_ROOT
from app.core.database import init_db, AsyncSessionLocal
from app.core.exceptions import register_exception_handlers
from app.core.redis import check_redis, close_redis
from app.modules.auth.service import bootstrap_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    print(f"[AgentForge] Starting server on {settings.SERVER_HOST}:{settings.SERVER_PORT}")
    print(f"[AgentForge] USE_API={settings.USE_API}")

    try:
        await init_db()
        print("[AgentForge] Database tables verified")
        # Bootstrap admin user if no users exist
        async with AsyncSessionLocal() as sess:
            await bootstrap_admin(sess)
    except Exception as e:
        print(f"[AgentForge] WARNING: Database not available yet: {e}")

    try:
        redis_ok = await check_redis()
        print(f"[AgentForge] Redis: {'connected' if redis_ok else 'unreachable'}")
    except Exception:
        print("[AgentForge] Redis: not available (will retry on first use)")

    yield

    print("[AgentForge] Shutting down...")
    await close_redis()


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
    """Detailed server status."""
    redis_ok = False
    db_ok = False
    try:
        redis_ok = await check_redis()
    except Exception:
        pass
    try:
        from app.core.database import async_engine
        async with async_engine.connect() as conn:
            await conn.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass

    return {
        "status": "running",
        "version": "0.1.0",
        "database": "connected" if db_ok else "unavailable",
        "redis": "connected" if redis_ok else "unavailable",
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
