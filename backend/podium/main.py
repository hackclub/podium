from contextlib import asynccontextmanager
from typing import AsyncIterator

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from podium.config import settings

# Initialize Sentry ASAP
if not settings.is_development:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        send_default_pii=True,
    )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Initialize Redis/Valkey client for cache operations
    from podium.cache.client import get_redis_client, close_redis_client
    
    try:
        client = get_redis_client()
        client.ping()
        print("✓ Redis/Valkey connection established")
    except Exception as e:
        print(f"⚠ Redis/Valkey connection failed: {e}")
        print("  Cache operations will fall back to Airtable")
    
    yield
    
    # Cleanup on shutdown
    close_redis_client()


app = FastAPI(lifespan=lifespan)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Airtable-Hits", "X-Cache"],
)


@app.middleware("http")
async def track_airtable_hits(request: Request, call_next):
    from podium.db.db import _current_request
    from podium.cache.operations import _cache_status

    request.state.airtable_hits = 0
    token_req = _current_request.set(request)

    # Create a per-request mutable cache status container
    cache_state = {"value": "BYPASS", "hits": 0, "misses": 0, "bypass": 0}
    token_cache = _cache_status.set(cache_state)

    try:
        response = await call_next(request)
        response.headers["X-Airtable-Hits"] = str(request.state.airtable_hits)
        # Use aggregate status: HIT if any hits, MISS if any misses (no hits), else BYPASS
        if cache_state["hits"] > 0:
            response.headers["X-Cache"] = f"HIT ({cache_state['hits']})"
        elif cache_state["misses"] > 0:
            response.headers["X-Cache"] = f"MISS ({cache_state['misses']})"
        else:
            response.headers["X-Cache"] = "BYPASS"
        return response
    finally:
        _current_request.reset(token_req)
        _cache_status.reset(token_cache)


# Dynamically import all routers from the routers directory
from pathlib import Path

routers_dir = Path(__file__).parent / "routers"
for router_file in routers_dir.glob("*.py"):
    if router_file.stem != "__init__":
        module = __import__(
            f"podium.routers.{router_file.stem}", fromlist=["router"]
        )
        if hasattr(module, "router"):
            app.include_router(module.router)


def main():
    import uvicorn

    uvicorn.run("podium.main:app", host="0.0.0.0", port=8000, reload=True)
