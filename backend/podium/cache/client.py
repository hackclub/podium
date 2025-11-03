"""Redis/Valkey client configuration."""

from redis import Redis
from podium.config import settings
from typing import Optional

_redis_client: Optional[Redis] = None


def get_redis_client() -> Redis:
    """
    Get or create the Redis/Valkey client singleton.
    
    Configure REDIS_URL in settings
    """
    global _redis_client
    
    if _redis_client is None:
        # redis_url = getattr(settings, "redis_url", "redis://localhost:6379")
        redis_url = getattr(settings, "redis_url")
        _redis_client = Redis.from_url(
            redis_url,
            decode_responses=False,  # redis-om handles encoding
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        
    return _redis_client


def close_redis_client():
    """Close the Redis connection (call on shutdown)."""
    global _redis_client
    if _redis_client:
        _redis_client.close()
        _redis_client = None
