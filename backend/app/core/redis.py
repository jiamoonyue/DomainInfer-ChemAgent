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
