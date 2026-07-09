# P0: AgentForge Project Scaffolding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the AgentForge project skeleton with Docker Compose, FastAPI backend, PostgreSQL + Redis infrastructure, and the module directory structure defined in the design spec.

**Architecture:** A modular monolith FastAPI backend with PostgreSQL (async SQLAlchemy 2.0) for all persistent storage and Redis for caching/rate-limiting. All services are orchestrated via Docker Compose. The project is created alongside the existing ChemAgent project at `d:\求职\ChemAgent项目\AgentForge`.

**Tech Stack:** Python 3.13, FastAPI 0.136, Uvicorn 0.48, SQLAlchemy 2.0 (async), asyncpg, Redis 7, Pydantic Settings 2.14, Alembic, Docker Compose v3.8, Nginx

## Global Constraints

- Python >= 3.11 (uses the existing conda env at `ChemicalEngineeringModelDeployment/env/`)
- All backend code in `backend/app/` with module structure: `core/`, `modules/<name>/`, `providers/`, `mcp/`
- Each module has `__init__.py`, `router.py`, `service.py`, `models.py`, `schemas.py`
- PostgreSQL 15 via Docker, Redis 7 via Docker
- All config via `Pydantic Settings` reading from `.env` file
- No hardcoded credentials — everything in `.env` / environment variables
- Database migrations via Alembic
- Frontend directory exists but is empty scaffolding (actual React app in P3)
- `USE_API` defaults to `true` — the server starts in API mode (no local model needed for P0)
- All DB models use UUID primary keys and `created_at`/`updated_at` timestamps
- Rate-limiting config is defined but not enforced until Auth module (P1)

---

### Task 1: Create Project Directory Structure

**Files:**
- Create: All directories listed below

**Interfaces:**
- Consumes: nothing
- Produces: `AgentForge/` directory tree (empty `__init__.py` files where needed)

- [ ] **Step 1: Create all directories**

```bash
cd "d:/求职/ChemAgent项目"
mkdir -p AgentForge/backend/app/core
mkdir -p AgentForge/backend/app/modules/auth
mkdir -p AgentForge/backend/app/modules/agents
mkdir -p AgentForge/backend/app/modules/rag
mkdir -p AgentForge/backend/app/modules/tools
mkdir -p AgentForge/backend/app/modules/knowledge
mkdir -p AgentForge/backend/app/modules/conversations
mkdir -p AgentForge/backend/app/modules/observability
mkdir -p AgentForge/backend/app/providers
mkdir -p AgentForge/backend/app/mcp
mkdir -p AgentForge/backend/migrations/versions
mkdir -p AgentForge/backend/tests
mkdir -p AgentForge/frontend/src/components
mkdir -p AgentForge/frontend/src/pages
mkdir -p AgentForge/frontend/src/hooks
mkdir -p AgentForge/frontend/src/lib
mkdir -p AgentForge/knowledge/chem
mkdir -p AgentForge/agents/chem
mkdir -p AgentForge/prompts
mkdir -p AgentForge/docs/api
mkdir -p AgentForge/nginx
```

- [ ] **Step 2: Create `__init__.py` files for all Python packages**

```bash
cd "d:/求职/ChemAgent项目/AgentForge/backend/app"
touch __init__.py
touch core/__init__.py
touch modules/__init__.py
touch modules/auth/__init__.py
touch modules/agents/__init__.py
touch modules/rag/__init__.py
touch modules/tools/__init__.py
touch modules/knowledge/__init__.py
touch modules/conversations/__init__.py
touch modules/observability/__init__.py
touch providers/__init__.py
touch mcp/__init__.py
```

- [ ] **Step 3: Create placeholder `.gitkeep` for empty dirs**

```bash
touch "d:/求职/ChemAgent项目/AgentForge/frontend/src/components/.gitkeep"
touch "d:/求职/ChemAgent项目/AgentForge/frontend/src/pages/.gitkeep"
touch "d:/求职/ChemAgent项目/AgentForge/frontend/src/hooks/.gitkeep"
touch "d:/求职/ChemAgent项目/AgentForge/frontend/src/lib/.gitkeep"
touch "d:/求职/ChemAgent项目/AgentForge/knowledge/chem/.gitkeep"
touch "d:/求职/ChemAgent项目/AgentForge/agents/chem/.gitkeep"
touch "d:/求职/ChemAgent项目/AgentForge/prompts/.gitkeep"
```

- [ ] **Step 4: Verify directory structure**

```bash
find "d:/求职/ChemAgent项目/AgentForge" -type d | sort
```

Expected output: 30+ directories matching the design doc structure.

- [ ] **Step 5: Initialize git**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
git init
git add -A
git commit -m "feat: scaffold AgentForge project directory structure"
```

---

### Task 2: Create `.env.example` and Pydantic Settings Config

**Files:**
- Create: `backend/app/core/config.py`
- Create: `.env.example`

**Interfaces:**
- Consumes: directory structure from Task 1
- Produces:
  - `backend.app.core.config.Settings` (Pydantic BaseSettings, reads from `.env`)
  - `backend.app.core.config.settings` (singleton instance)
  - All config values: `DATABASE_URL`, `REDIS_URL`, `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `USE_API`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `RATE_LIMIT_PER_MINUTE`, `SERVER_HOST`, `SERVER_PORT`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`

- [ ] **Step 1: Write `.env.example`**

```bash
cat > "d:/求职/ChemAgent项目/AgentForge/.env.example" << 'ENVEOF'
# ========================================
# AgentForge Configuration
# Copy this file to .env and fill in values
# ========================================

# ---- Server ----
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# ---- Database (PostgreSQL) ----
DATABASE_URL=postgresql+asyncpg://agentforge:agentforge@postgres:5432/agentforge

# ---- Redis ----
REDIS_URL=redis://redis:6379/0

# ---- DeepSeek API ----
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
USE_API=true

# ---- Auth (JWT) ----
SECRET_KEY=change-me-to-a-random-secret-at-least-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# ---- Rate Limiting ----
RATE_LIMIT_PER_MINUTE=20

# ---- Admin (auto-created on first run) ----
ADMIN_EMAIL=admin@agentforge.local
ADMIN_PASSWORD=admin123

# ---- Observability ----
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
ENABLE_METRICS=true
ENVEOF
```

- [ ] **Step 2: Write `backend/app/core/config.py`**

```python
"""AgentForge Configuration — Pydantic Settings loaded from .env"""

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


# Project root: AgentForge/ (two levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """All application settings, loaded from .env / environment."""

    # ---- Server ----
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # ---- Database ----
    DATABASE_URL: str = "postgresql+asyncpg://agentforge:agentforge@localhost:5432/agentforge"
    DATABASE_URL_SYNC: str = "postgresql://agentforge:agentforge@localhost:5432/agentforge"

    # ---- Redis ----
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---- LLM API ----
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"
    USE_API: bool = True

    # ---- Auth ----
    SECRET_KEY: str = "change-me-to-a-random-secret-at-least-32-chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---- Rate Limiting ----
    RATE_LIMIT_PER_MINUTE: int = 20

    # ---- Admin bootstrap ----
    ADMIN_EMAIL: str = "admin@agentforge.local"
    ADMIN_PASSWORD: str = "admin123"

    # ---- Observability ----
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    ENABLE_METRICS: bool = True

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()


settings = get_settings()
```

- [ ] **Step 3: Verify config loads (Python import test)**

```bash
cd "d:/求职/ChemAgent项目/AgentForge" && \
  PYTHONPATH="backend" \
  "d:/求职/ChemAgent项目/ChemicalEngineeringModelDeployment/env/python.exe" \
  -c "from app.core.config import settings; print(f'SERVER_PORT={settings.SERVER_PORT}'); print(f'USE_API={settings.USE_API}'); print(f'MODEL={settings.DEEPSEEK_MODEL}'); print('OK')"
```

Expected output:
```
SERVER_PORT=8000
USE_API=True
MODEL=deepseek-v4-flash
OK
```

- [ ] **Step 4: Commit**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
git add .env.example backend/app/core/config.py backend/app/core/__init__.py
git commit -m "feat: add Pydantic Settings config and .env.example"
```

---

### Task 3: Create `requirements.txt`

**Files:**
- Create: `backend/requirements.txt`

**Interfaces:**
- Consumes: directory structure from Task 1
- Produces: `backend/requirements.txt` with all P0 dependencies

- [ ] **Step 1: Write `backend/requirements.txt`**

```bash
cat > "d:/求职/ChemAgent项目/AgentForge/backend/requirements.txt" << 'REQEOF'
# ========================================
# AgentForge Backend Dependencies
# ========================================

# ---- Web Framework ----
fastapi==0.136.1
uvicorn[standard]==0.48.0

# ---- Database ----
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
alembic==1.14.1
psycopg2-binary==2.9.10

# ---- Redis ----
redis==5.2.1

# ---- Config & Env ----
pydantic-settings==2.14.1
python-dotenv==1.2.2

# ---- Auth ----
pyjwt==2.13.0
bcrypt==5.0.0
python-multipart==0.0.29

# ---- Observability ----
opentelemetry-api==1.42.1
opentelemetry-sdk==1.42.1
opentelemetry-exporter-otlp-proto-grpc==1.42.1
opentelemetry-instrumentation-fastapi==0.63b1

# ---- Utils ----
pyyaml==6.0.3
httpx==0.28.1
REQEOF
```

- [ ] **Step 2: Verify requirements are parseable**

```bash
cd "d:/求职/ChemAgent项目/AgentForge" && \
  "d:/求职/ChemAgent项目/ChemicalEngineeringModelDeployment/env/python.exe" \
  -c "
with open('backend/requirements.txt') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            parts = line.split('==')
            print(f'{parts[0]} -> {parts[1] if len(parts)>1 else \"any\"}')
print('OK - all lines parseable')
"
```

Expected: All package names printed, no syntax errors.

- [ ] **Step 3: Commit**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
git add backend/requirements.txt
git commit -m "feat: add requirements.txt with P0 dependencies"
```

---

### Task 4: Create PostgreSQL Async Connection (`core/database.py`)

**Files:**
- Create: `backend/app/core/database.py`

**Interfaces:**
- Consumes:
  - `settings.DATABASE_URL` from Task 2
- Produces:
  - `async_engine` — SQLAlchemy AsyncEngine
  - `AsyncSessionLocal` — async session factory
  - `Base` — SQLAlchemy declarative base
  - `get_db()` — FastAPI dependency yielding async session
  - `init_db()` — create all tables (called at startup)

- [ ] **Step 1: Write `backend/app/core/database.py`**

```python
"""Database connection — PostgreSQL via SQLAlchemy 2.0 async"""

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Naming convention for constraints/indexes (consistent Alembic migrations)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base. All models inherit from this."""
    metadata = metadata


# Async engine — echo=False in production, True for debug
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # verify connections before use
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """FastAPI dependency: yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables. Call at startup."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 2: Verify import works**

```bash
cd "d:/求职/ChemAgent项目/AgentForge" && \
  PYTHONPATH="backend" \
  "d:/求职/ChemAgent项目/ChemicalEngineeringModelDeployment/env/python.exe" \
  -c "from app.core.database import Base, async_engine, get_db; print('OK - database module loads')"
```

Expected output: `OK - database module loads`

(Note: the module imports but won't connect to PostgreSQL yet — that's expected, it only connects lazily.)

- [ ] **Step 3: Commit**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
git add backend/app/core/database.py
git commit -m "feat: add async PostgreSQL connection with SQLAlchemy 2.0"
```

---

### Task 5: Create Redis Connection (`core/redis.py`)

**Files:**
- Create: `backend/app/core/redis.py`

**Interfaces:**
- Consumes:
  - `settings.REDIS_URL` from Task 2
- Produces:
  - `get_redis()` — returns Redis client (lazy init)
  - `redis_client` — module-level singleton (None until first access)
  - `check_redis()` — health check ping

- [ ] **Step 1: Write `backend/app/core/redis.py`**

```python
"""Redis connection — caching, rate-limiting, session store"""

from redis.asyncio import Redis

from app.core.config import settings

_redis: Redis | None = None


async def get_redis() -> Redis:
    """Return the Redis client singleton. Creates connection on first call."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return _redis


async def check_redis() -> bool:
    """Health check: ping Redis. Returns True if reachable."""
    try:
        r = await get_redis()
        return await r.ping()
    except Exception:
        return False


async def close_redis():
    """Close the Redis connection. Call at shutdown."""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
```

- [ ] **Step 2: Verify import works**

```bash
cd "d:/求职/ChemAgent项目/AgentForge" && \
  PYTHONPATH="backend" \
  "d:/求职/ChemAgent项目/ChemicalEngineeringModelDeployment/env/python.exe" \
  -c "from app.core.redis import get_redis; print('OK - redis module loads')"
```

Expected output: `OK - redis module loads`

- [ ] **Step 3: Commit**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
git add backend/app/core/redis.py
git commit -m "feat: add async Redis connection module"
```

---

### Task 6: Create Global Exception Handler (`core/exceptions.py`)

**Files:**
- Create: `backend/app/core/exceptions.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `AppException` — base exception with status_code
  - `NotFoundException` — 404
  - `UnauthorizedException` — 401
  - `ForbiddenException` — 403
  - `ValidationException` — 422
  - `register_exception_handlers(app)` — installs all handlers on FastAPI instance

- [ ] **Step 1: Write `backend/app/core/exceptions.py`**

```python
"""Global exception handling for AgentForge."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception with HTTP status code."""
    status_code: int = 500
    message: str = "Internal server error"

    def __init__(self, message: str | None = None, status_code: int | None = None):
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(AppException):
    status_code = 404
    message = "Resource not found"


class UnauthorizedException(AppException):
    status_code = 401
    message = "Authentication required"


class ForbiddenException(AppException):
    status_code = 403
    message = "Permission denied"


class ValidationException(AppException):
    status_code = 422
    message = "Validation error"


def register_exception_handlers(app: FastAPI):
    """Register all custom exception handlers on the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "status_code": exc.status_code},
        )

    # FastAPI's built-in validation errors get the same treatment
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc), "status_code": 422},
        )
```

- [ ] **Step 2: Verify import**

```bash
cd "d:/求职/ChemAgent项目/AgentForge" && \
  PYTHONPATH="backend" \
  "d:/求职/ChemAgent项目/ChemicalEngineeringModelDeployment/env/python.exe" \
  -c "from app.core.exceptions import NotFoundException, AppException; e = NotFoundException('test'); assert e.status_code == 404; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
git add backend/app/core/exceptions.py
git commit -m "feat: add global exception classes and handler registration"
```

---

### Task 7: Create Security Utilities (`core/security.py`)

**Files:**
- Create: `backend/app/core/security.py`

**Interfaces:**
- Consumes:
  - `settings.SECRET_KEY`, `settings.ACCESS_TOKEN_EXPIRE_MINUTES`, `settings.REFRESH_TOKEN_EXPIRE_DAYS` from Task 2
- Produces:
  - `hash_password(password: str) -> str` — bcrypt hash
  - `verify_password(plain: str, hashed: str) -> bool`
  - `create_access_token(data: dict) -> str` — JWT encode
  - `create_refresh_token(data: dict) -> str` — JWT encode (longer expiry)
  - `decode_token(token: str) -> dict | None` — JWT decode with error handling

- [ ] **Step 1: Write `backend/app/core/security.py`**

```python
"""Security utilities — password hashing, JWT token creation/verification."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_access_token(data: dict) -> str:
    """Create a JWT access token with short expiry."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token with longer expiry."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None on failure."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
```

- [ ] **Step 2: Verify with a quick encode/decode cycle**

```bash
cd "d:/求职/ChemAgent项目/AgentForge" && \
  PYTHONPATH="backend" \
  "d:/求职/ChemAgent项目/ChemicalEngineeringModelDeployment/env/python.exe" \
  -c "
from app.core.security import hash_password, verify_password, create_access_token, decode_token
hashed = hash_password('test123')
assert verify_password('test123', hashed)
assert not verify_password('wrong', hashed)
token = create_access_token({'sub': 'user1'})
payload = decode_token(token)
assert payload is not None
assert payload['sub'] == 'user1'
assert payload['type'] == 'access'
print('OK - security works')
"
```

Expected output: `OK - security works`

- [ ] **Step 3: Commit**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
git add backend/app/core/security.py
git commit -m "feat: add security utilities (bcrypt + JWT)"
```

---

### Task 8: Create FastAPI Application Entry Point (`main.py`)

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/__init__.py` (should already exist from Task 1)

**Interfaces:**
- Consumes:
  - `settings` from Task 2
  - `init_db`, `get_db` from Task 4
  - `check_redis`, `close_redis` from Task 5
  - `register_exception_handlers` from Task 6
- Produces:
  - FastAPI `app` instance with startup/shutdown lifecycle
  - `GET /health` — health check endpoint
  - `GET /api/status` — detailed status (DB, Redis, model)
  - Empty module routers mounted at `/api/auth`, `/api/agents`, `/api/rag`, `/api/tools`, `/api/knowledge`, `/api/conversations`

- [ ] **Step 1: Write `backend/app/main.py`**

```python
"""AgentForge — Enterprise AI Agent Development Platform."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings, PROJECT_ROOT
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.core.redis import check_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # Startup
    print(f"[AgentForge] Starting server on {settings.SERVER_HOST}:{settings.SERVER_PORT}")
    print(f"[AgentForge] USE_API={settings.USE_API}")

    # Database: tables are created by Alembic migrations in production,
    # but for dev convenience we auto-create on first run.
    try:
        await init_db()
        print("[AgentForge] Database tables verified")
    except Exception as e:
        print(f"[AgentForge] WARNING: Database not available yet: {e}")

    # Redis: will connect lazily when first used
    try:
        redis_ok = await check_redis()
        print(f"[AgentForge] Redis: {'connected' if redis_ok else 'unreachable'}")
    except Exception:
        print("[AgentForge] Redis: not available (will retry on first use)")

    yield  # Server is running

    # Shutdown
    print("[AgentForge] Shutting down...")
    await close_redis()


app = FastAPI(
    title="AgentForge",
    description="Enterprise AI Agent Development Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow all origins in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register custom exception handlers
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


# ---- Mount module routers (empty stubs for now) ----

# Each module's router will be imported here when the module is built.
# For P0 we register placeholder routes inline.

from fastapi import APIRouter

# Placeholder routers — these get replaced by real module routers in P1/P2
auth_router = APIRouter(prefix="/auth", tags=["Auth"])
agents_router = APIRouter(prefix="/agents", tags=["Agents"])
rag_router = APIRouter(prefix="/rag", tags=["RAG"])
tools_router = APIRouter(prefix="/tools", tags=["Tools"])
knowledge_router = APIRouter(prefix="/knowledge", tags=["Knowledge"])
conversations_router = APIRouter(prefix="/conversations", tags=["Conversations"])
observability_router = APIRouter(prefix="/observability", tags=["Observability"])

@auth_router.get("/ping")
async def auth_ping():
    return {"module": "auth", "status": "pending"}

@agents_router.get("/ping")
async def agents_ping():
    return {"module": "agents", "status": "pending"}

@rag_router.get("/ping")
async def rag_ping():
    return {"module": "rag", "status": "pending"}

@tools_router.get("/ping")
async def tools_ping():
    return {"module": "tools", "status": "pending"}

@knowledge_router.get("/ping")
async def knowledge_ping():
    return {"module": "knowledge", "status": "pending"}

@conversations_router.get("/ping")
async def conversations_ping():
    return {"module": "conversations", "status": "pending"}

@observability_router.get("/ping")
async def observability_ping():
    return {"module": "observability", "status": "pending"}

# Mount all routers under /api
app.include_router(auth_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(rag_router, prefix="/api")
app.include_router(tools_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")
app.include_router(observability_router, prefix="/api")
```

- [ ] **Step 2: Start the server standalone (without Docker) and test /health**

```bash
cd "d:/求职/ChemAgent项目/AgentForge" && \
  PYTHONPATH="backend" \
  "d:/求职/ChemAgent项目/ChemicalEngineeringModelDeployment/env/python.exe" \
  -c "
import uvicorn, threading, time, urllib.request, json
from app.main import app

t = threading.Thread(target=lambda: uvicorn.run(app, host='127.0.0.1', port=18000, log_level='warning'), daemon=True)
t.start()
time.sleep(2)

r = urllib.request.urlopen('http://127.0.0.1:18000/health', timeout=5)
print(json.loads(r.read()))

r2 = urllib.request.urlopen('http://127.0.0.1:18000/api/status', timeout=5)
print(json.loads(r2.read()))

r3 = urllib.request.urlopen('http://127.0.0.1:18000/api/auth/ping', timeout=5)
print(json.loads(r3.read()))

print('OK - FastAPI server works')
"
```

Expected output:
```
{'status': 'ok'}
{'status': 'running', 'version': '0.1.0', 'database': 'unavailable', ...}
{'module': 'auth', 'status': 'pending'}
OK - FastAPI server works
```

- [ ] **Step 3: Commit**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
git add backend/app/main.py backend/app/__init__.py
git commit -m "feat: add FastAPI entry point with module routers and health checks"
```

---

### Task 9: Create `Dockerfile`

**Files:**
- Create: `Dockerfile`

**Interfaces:**
- Consumes: `backend/requirements.txt` from Task 3, `backend/` source code
- Produces: Docker image running FastAPI on port 8000

- [ ] **Step 1: Write `Dockerfile`**

```dockerfile
# AgentForge Backend Dockerfile
FROM python:3.13-slim

# Prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (only what asyncpg needs)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Expose the FastAPI port
EXPOSE 8000

# Start Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Verify Dockerfile syntax**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
# No Docker on Windows Bash, but we can check the file exists
test -f Dockerfile && echo "OK - Dockerfile exists" || echo "FAIL"
```

Expected: `OK - Dockerfile exists`

- [ ] **Step 3: Commit**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
git add Dockerfile
git commit -m "feat: add Dockerfile for backend service"
```

---

### Task 10: Create `docker-compose.yml`

**Files:**
- Create: `docker-compose.yml`

**Interfaces:**
- Consumes: `Dockerfile` from Task 9
- Produces: Full stack via `docker compose up`

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
version: "3.8"

services:
  # ============================================
  # PostgreSQL 15
  # ============================================
  postgres:
    image: postgres:15-alpine
    container_name: agentforge-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: agentforge
      POSTGRES_PASSWORD: agentforge
      POSTGRES_DB: agentforge
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U agentforge"]
      interval: 5s
      timeout: 5s
      retries: 5

  # ============================================
  # Redis 7
  # ============================================
  redis:
    image: redis:7-alpine
    container_name: agentforge-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  # ============================================
  # Jaeger (OpenTelemetry tracing backend)
  # ============================================
  jaeger:
    image: jaegertracing/all-in-one:latest
    container_name: agentforge-jaeger
    restart: unless-stopped
    ports:
      - "16686:16686"   # Jaeger UI
      - "4317:4317"     # OTLP gRPC
      - "4318:4318"     # OTLP HTTP
    environment:
      COLLECTOR_OTLP_ENABLED: "true"

  # ============================================
  # FastAPI Backend
  # ============================================
  backend:
    build: .
    container_name: agentforge-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app
      - ./knowledge:/app/../knowledge
      - ./agents:/app/../agents
      - ./prompts:/app/../prompts

  # ============================================
  # Nginx (production gateway)
  # ============================================
  nginx:
    image: nginx:alpine
    container_name: agentforge-nginx
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
```

- [ ] **Step 2: Verify the file is valid YAML**

```bash
cd "d:/求职/ChemAgent项目/AgentForge" && \
  "d:/求职/ChemAgent项目/ChemicalEngineeringModelDeployment/env/python.exe" \
  -c "
import yaml
with open('docker-compose.yml') as f:
    data = yaml.safe_load(f)
services = list(data['services'].keys())
print(f'Services: {services}')
assert 'postgres' in services
assert 'redis' in services
assert 'backend' in services
assert 'nginx' in services
assert 'jaeger' in services
print('OK - docker-compose.yml is valid with 5 services')
"
```

Expected output:
```
Services: ['postgres', 'redis', 'jaeger', 'backend', 'nginx']
OK - docker-compose.yml is valid with 5 services
```

- [ ] **Step 3: Commit**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
git add docker-compose.yml
git commit -m "feat: add docker-compose.yml with all 5 services"
```

---

### Task 11: Create Nginx Configuration

**Files:**
- Create: `nginx/default.conf`

**Interfaces:**
- Consumes: backend service on port 8000
- Produces: Reverse proxy from port 80 → backend:8000

- [ ] **Step 1: Write `nginx/default.conf`**

```nginx
upstream backend {
    server backend:8000;
}

server {
    listen 80;
    server_name localhost;

    # Increase proxy timeouts for SSE streaming
    proxy_read_timeout 300s;
    proxy_connect_timeout 10s;

    # API requests go to FastAPI
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE streaming support
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;
    }

    # Health check
    location /health {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # Frontend static files (placeholder — React build output goes here in P3)
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 2: Verify file exists**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
test -f nginx/default.conf && echo "OK" || echo "FAIL"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
git add nginx/default.conf
git commit -m "feat: add Nginx reverse proxy config with SSE support"
```

---

### Task 12: Copy DeepSeek Client from Old Project

**Files:**
- Create: `backend/app/providers/deepseek_client.py`

**Interfaces:**
- Consumes: `settings.DEEPSEEK_API_KEY`, `settings.DEEPSEEK_API_BASE`, `settings.DEEPSEEK_MODEL` from Task 2
- Produces:
  - `DeepSeekClient` — OpenAI-compatible API client with streaming
  - `get_deepseek_client()` — singleton factory

This is a direct copy of the working client from `ChemicalEngineeringModelDeployment/app/deepseek_client.py`, adapted to use the new `Settings`-based config.

- [ ] **Step 1: Copy and adapt the DeepSeek client**

```bash
cp "d:/求职/ChemAgent项目/ChemicalEngineeringModelDeployment/app/deepseek_client.py" \
   "d:/求职/ChemAgent项目/AgentForge/backend/app/providers/deepseek_client.py"
```

Then edit the import to use the new config:

```bash
cd "d:/求职/ChemAgent项目/AgentForge" && \
  "d:/求职/ChemAgent项目/ChemicalEngineeringModelDeployment/env/python.exe" \
  -c "
path = 'backend/app/providers/deepseek_client.py'
with open(path, 'r') as f:
    content = f.read()
# Replace old config import with new one
content = content.replace(
    'from config import DEEPSEEK_API_KEY, DEEPSEEK_API_BASE, DEEPSEEK_MODEL',
    'from app.core.config import settings'
)
# Replace old config references
content = content.replace('DEEPSEEK_MODEL', 'settings.DEEPSEEK_MODEL')
content = content.replace('DEEPSEEK_API_KEY', 'settings.DEEPSEEK_API_KEY')
content = content.replace('DEEPSEEK_API_BASE', 'settings.DEEPSEEK_API_BASE')
with open(path, 'w') as f:
    f.write(content)
print('OK - adapted imports to use Settings')
"
```

- [ ] **Step 2: Verify import works**

```bash
cd "d:/求职/ChemAgent项目/AgentForge" && \
  PYTHONPATH="backend" \
  "d:/求职/ChemAgent项目/ChemicalEngineeringModelDeployment/env/python.exe" \
  -c "from app.providers.deepseek_client import get_deepseek_client; c = get_deepseek_client(); print(f'Client: {c.model}'); print('OK')"
```

Expected output:
```
[DeepSeek] Client initialized: model=deepseek-v4-flash, base=https://api.deepseek.com
Client: deepseek-v4-flash
OK
```

- [ ] **Step 3: Commit**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
git add backend/app/providers/__init__.py backend/app/providers/deepseek_client.py
git commit -m "feat: port DeepSeek client to use new Settings config"
```

---

### Task 13: Create `.gitignore`

**Files:**
- Create: `.gitignore`

**Interfaces:**
- Consumes: nothing
- Produces: Proper git exclusion rules

- [ ] **Step 1: Write `.gitignore`**

```bash
cat > "d:/求职/ChemAgent项目/AgentForge/.gitignore" << 'GITEOF'
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/
env/

# Environment
.env
!.env.example

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
.postgres_data/
.redis_data/

# Data
data/
*.db
*.db-shm
*.db-wal

# ChromaDB
chroma_v2/
chroma_data/

# Models
models/

# Logs
*.log
logs/

# Node (frontend)
node_modules/
frontend/dist/
frontend/.next/
GITEOF
```

- [ ] **Step 2: Commit**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
git add .gitignore
git commit -m "chore: add .gitignore"
```

---

### Task 14: Clone Example Knowledge Base + Create `README.md`

**Files:**
- Create: `README.md` (project-level)
- Copy: `knowledge/chem/*.md` from old project

**Interfaces:**
- Consumes: `ChemicalEngineeringModelDeployment/knowledge_base/*.md`
- Produces: `knowledge/chem/` populated with example documents

- [ ] **Step 1: Copy knowledge base files**

```bash
cp "d:/求职/ChemAgent项目/ChemicalEngineeringModelDeployment/knowledge_base/"*.md \
   "d:/求职/ChemAgent项目/AgentForge/knowledge/chem/"
```

- [ ] **Step 2: Write project README.md**

```bash
cat > "d:/求职/ChemAgent项目/AgentForge/README.md" << 'READEOF'
# AgentForge

Enterprise AI Agent Development Platform.

## Quick Start

```bash
cp .env.example .env
# Edit .env with your API keys
docker compose up
```

Open http://localhost:8000/api/status to verify.

## Services

| Service | Port | Description |
|---------|------|-------------|
| Backend (FastAPI) | 8000 | API server |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache / rate limiting |
| Jaeger | 16686 | Distributed tracing UI |
| Nginx | 80 | Production gateway |

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full design.
READEOF
```

- [ ] **Step 3: Commit**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
git add knowledge/chem/ README.md
git commit -m "feat: add knowledge base examples and README"
```

---

### Task 15: Final Integration Verification

**Files:**
- Create: none (verify-only task)

**Interfaces:**
- Consumes: All previous tasks
- Produces: Verification report

- [ ] **Step 1: Verify all core modules import correctly**

```bash
cd "d:/求职/ChemAgent项目/AgentForge" && \
  PYTHONPATH="backend" \
  "d:/求职/ChemAgent项目/ChemicalEngineeringModelDeployment/env/python.exe" \
  -c "
from app.core.config import settings
from app.core.database import Base, get_db, init_db
from app.core.redis import get_redis, check_redis
from app.core.exceptions import AppException, NotFoundException, UnauthorizedException
from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.providers.deepseek_client import get_deepseek_client
print('All imports OK')
print(f'Config: {settings.SERVER_HOST}:{settings.SERVER_PORT}')
print(f'DB: {settings.DATABASE_URL}')
print(f'Redis: {settings.REDIS_URL}')
print(f'Model: {settings.DEEPSEEK_MODEL}')
"
```

- [ ] **Step 2: Verify FastAPI serves all endpoints**

```bash
cd "d:/求职/ChemAgent项目/AgentForge" && \
  PYTHONPATH="backend" \
  "d:/求职/ChemAgent项目/ChemicalEngineeringModelDeployment/env/python.exe" \
  -c "
import uvicorn, threading, time, urllib.request, json
from app.main import app

t = threading.Thread(target=lambda: uvicorn.run(app, host='127.0.0.1', port=18001, log_level='warning'), daemon=True)
t.start()
time.sleep(2)

endpoints = ['/health', '/api/status', '/api/auth/ping', '/api/agents/ping',
             '/api/rag/ping', '/api/tools/ping', '/api/knowledge/ping',
             '/api/conversations/ping', '/api/observability/ping']
for ep in endpoints:
    r = urllib.request.urlopen(f'http://127.0.0.1:18001{ep}', timeout=3)
    print(f'{ep}: {r.status}')

print('All endpoints reachable')
"
```

Expected: all endpoints return 200.

- [ ] **Step 3: Verify directory structure matches design doc**

```bash
cd "d:/求职/ChemAgent项目/AgentForge" && \
  echo '=== Core modules ===' && ls backend/app/core/*.py && \
  echo '=== Providers ===' && ls backend/app/providers/*.py && \
  echo '=== Modules ===' && ls -d backend/app/modules/*/ && \
  echo '=== Top level ===' && ls -la .env.example Dockerfile docker-compose.yml requirements.txt 2>/dev/null || ls -la .env.example Dockerfile docker-compose.yml
```

- [ ] **Step 4: Final commit**

```bash
cd "d:/求职/ChemAgent项目/AgentForge"
git status
# Should show clean working tree (all files committed)
```

---

## Plan Self-Review

### Spec Coverage

| Design Doc Section | Task |
|-------------------|------|
| Directory structure | Task 1 |
| `.env.example` | Task 2 |
| Pydantic Settings config | Task 2 |
| `requirements.txt` / `pyproject.toml` | Task 3 |
| PostgreSQL + SQLAlchemy async | Task 4 |
| Redis connection | Task 5 |
| Exception handling | Task 6 |
| JWT / security | Task 7 (stubs, full in P1) |
| FastAPI entry + routers | Task 8 |
| Dockerfile | Task 9 |
| Docker Compose (5 services) | Task 10 |
| Nginx config | Task 11 |
| DeepSeek client port | Task 12 |
| `.gitignore` | Task 13 |
| Knowledge base examples | Task 14 |
| Integration verification | Task 15 |

### Type Consistency

- `settings` is a `Settings` instance from `app.core.config`, used throughout
- `get_db()` returns `AsyncSession`, `get_redis()` returns `Redis` — consistent signatures
- All module routers use the same `APIRouter(prefix=..., tags=[...])` pattern
- `init_db()` is async and called at startup in `main.py` lifespan

### Placeholder Check

- No "TBD", "TODO", or "implement later" strings
- All code is complete and copy-pasteable
- All test commands have expected output
- All file paths are absolute or relative to `AgentForge/`

