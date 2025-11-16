"""Middleware for cache instrumentation and metrics."""

from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable to track cache stats per request
cache_stats: ContextVar[dict] = ContextVar("cache_stats", default={"hits": 0, "misses": 0, "airtable_calls": 0})


class CacheInstrumentationMiddleware(BaseHTTPMiddleware):
    """Add X-Cache headers to track cache hit/miss rates."""
    
    async def dispatch(self, request: Request, call_next):
        # Initialize cache stats for this request
        cache_stats.set({"hits": 0, "misses": 0, "airtable_calls": 0})
        
        # Process request
        response = await call_next(request)
        
        # Get final stats
        stats = cache_stats.get()
        hits = stats.get("hits", 0)
        misses = stats.get("misses", 0)
        airtable_calls = stats.get("airtable_calls", 0)
        
        # Determine cache status
        if hits > 0 and misses == 0:
            cache_status = "HIT"
        elif hits == 0 and misses > 0:
            cache_status = "MISS"
        elif hits > 0 and misses > 0:
            cache_status = "MIXED"
        else:
            cache_status = "BYPASS"
        
        # Add headers
        response.headers["X-Cache"] = cache_status
        response.headers["X-Cache-Hits"] = str(hits)
        response.headers["X-Cache-Misses"] = str(misses)
        response.headers["X-Airtable-Calls"] = str(airtable_calls)
        
        return response
