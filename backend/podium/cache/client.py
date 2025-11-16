"""Redis/Valkey async client configuration."""

from redis.asyncio import Redis
from podium.config import settings
from typing import Optional

_redis_client: Optional[Redis] = None


def get_redis_client() -> Redis:
    """
    Get or create the async Redis/Valkey client singleton.
    
    Configure REDIS_URL in settings
    """
    global _redis_client
    
    if _redis_client is None:
        redis_url = getattr(settings, "redis_url")
        _redis_client = Redis.from_url(
            redis_url,
            decode_responses=False,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        
    return _redis_client


async def close_redis_client():
    """Close the async Redis connection (call on shutdown)."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
