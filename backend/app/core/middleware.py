"""Global middleware — auth enforcement + rate limiting.

Design doc 6.1:
  - All /api/* require Authorization (except login/register)
  - Redis rate limit: 20 req/min per user
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.deps import get_optional_user_no_raise
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.core.config import settings

# Public endpoints that don't need auth
PUBLIC_PATHS = {
    "/api/auth/register",
    "/api/auth/login",
    "/api/auth/refresh",
    "/health",
    "/api/status",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# Public prefixes — any path starting with these is public
PUBLIC_PREFIXES = {
    "/api/tools",        # Tool registry + execution is public (MCP protocol)
    "/api/agents/ping",  # Health check
    "/api/rag/ping",
    "/api/tools/ping",
    "/api/knowledge/ping",
    "/api/observability/ping",
    "/api/agents",       # Agent discovery is public
    "/api/knowledge/namespaces",  # Namespace listing is public
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Enforce JWT/auth on all /api/* routes except public paths."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Allow OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip public paths
        if path in PUBLIC_PATHS or not path.startswith("/api/"):
            return await call_next(request)

        # Allow ping endpoints without auth (for health checks)
        if path.endswith("/ping"):
            return await call_next(request)

        # Allow public prefixes
        for prefix in PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Check auth header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return Response(
                content='{"detail":"Missing authorization header","status_code":401}',
                status_code=401,
                media_type="application/json",
            )

        try:
            async with AsyncSessionLocal() as sess:
                user = await get_optional_user_no_raise(auth_header, sess)
                if user is None:
                    return Response(
                        content='{"detail":"Invalid or expired token","status_code":401}',
                        status_code=401,
                        media_type="application/json",
                    )
                # Attach user to request state for downstream use
                request.state.user = user
        except Exception:
            return Response(
                content='{"detail":"Authentication error","status_code":401}',
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-based rate limiter. Design doc 6.1: 20 req/min per user."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Skip non-API and public paths
        if not path.startswith("/api/") or path in PUBLIC_PATHS:
            return await call_next(request)

        # Get user identity for rate limiting
        user_id = "anonymous"
        if hasattr(request.state, "user") and request.state.user:
            user_id = str(request.state.user.id)

        # Check rate limit via Redis
        try:
            redis = await get_redis()
            key = f"ratelimit:{user_id}:{int(time.time() / 60)}"
            count = await redis.incr(key)
            await redis.expire(key, 60)
            limit = settings.RATE_LIMIT_PER_MINUTE
            if count > limit:
                return Response(
                    content=f'{{"detail":"Rate limit exceeded ({limit}/min)","status_code":429}}',
                    status_code=429,
                    media_type="application/json",
                )
        except Exception:
            pass  # Redis unavailable — allow through

        return await call_next(request)
