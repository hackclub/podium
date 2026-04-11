"""
Redis caching helpers.

Provides simple get/set/delete wrappers with JSON serialization.
If Redis is not configured (redis_url is empty), all operations are silent no-ops
so the app works normally without a Redis instance.

Usage:
    from podium.cache import cache_get, cache_set, cache_delete

    # Cache a value for 30 seconds
    await cache_set("leaderboard:event-id", data, ttl=30)
    cached = await cache_get("leaderboard:event-id")
"""

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from podium.config import settings

logger = logging.getLogger(__name__)

# Module-level client — initialized by init_redis(), None if not configured
_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    """Connect to Redis. Called from the FastAPI lifespan on startup."""
    global _redis
    url = settings.get("redis_url", "")
    if not url:
        logger.info("Redis not configured (redis_url empty) — caching disabled")
        return
    try:
        _redis = aioredis.from_url(url, decode_responses=True)
        await _redis.ping()
        # Redact credentials from URL before logging (redis://:password@host/db)
        safe_url = url.split("@")[-1] if "@" in url else url
        logger.info("Redis connected: %s", safe_url)
    except Exception as exc:
        logger.warning("Redis unavailable: %s — caching disabled", exc)
        _redis = None


async def close_redis() -> None:
    """Disconnect from Redis. Called from the FastAPI lifespan on shutdown."""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


async def cache_get(key: str) -> Any | None:
    """Return the cached value for key, or None if not found / Redis unavailable."""
    if not _redis:
        return None
    try:
        value = await _redis.get(key)
        return json.loads(value) if value is not None else None
    except Exception as exc:
        logger.warning("cache_get(%s) failed: %s", key, exc)
        return None


async def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    """Store value as JSON under key with a TTL in seconds. Silently skips if Redis unavailable."""
    if not _redis:
        return
    try:
        await _redis.set(key, json.dumps(value), ex=ttl)
    except Exception as exc:
        logger.warning("cache_set(%s) failed: %s", key, exc)


async def cache_delete(key: str) -> None:
    """Delete a cached key. Silently skips if Redis unavailable."""
    if not _redis:
        return
    try:
        await _redis.delete(key)
    except Exception as exc:
        logger.warning("cache_delete(%s) failed: %s", key, exc)
