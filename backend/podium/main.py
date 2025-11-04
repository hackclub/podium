import importlib
import os
from pathlib import Path
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import AsyncIterator
import sentry_sdk


sentry_sdk.init(
    dsn=""
    if os.getenv("ENV_FOR_DYNACONF") == "development"
    else "https://489f4a109d07aeadfd13387bcd3197ab@o4508979744210944.ingest.de.sentry.io/4508979747553360",
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Initialize Redis/Valkey client for cache operations
    from podium.cache.client import get_redis_client, close_redis_client
    from podium.cache.models import (
        ProjectCache,
        EventCache,
        UserCache,
        VoteCache,
        ReferralCache,
    )
    
    try:
        client = get_redis_client()
        client.ping()  # Verify connection
        print("✓ Redis/Valkey connection established")
        
        # Create RediSearch indices at startup (idempotent)
        print("Creating RediSearch indices...")
        for model_name, model in [
            ("ProjectCache", ProjectCache),
            ("EventCache", EventCache),
            ("UserCache", UserCache),
            ("VoteCache", VoteCache),
            ("ReferralCache", ReferralCache),
        ]:
            try:
                model.create_index()
                print(f"  ✓ {model_name} index created")
            except Exception as e:
                # Index might already exist or RediSearch not available
                print(f"  ℹ {model_name} index: {e}")
        
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
    cache_state = {"value": "BYPASS"}
    token_cache = _cache_status.set(cache_state)

    try:
        response = await call_next(request)
        response.headers["X-Airtable-Hits"] = str(request.state.airtable_hits)
        response.headers["X-Cache"] = cache_state["value"]
        return response
    finally:
        _current_request.reset(token_req)
        _cache_status.reset(token_cache)


# Annotated
# https://fastapi.tiangolo.com/tutorial/path-params-numeric-validations/#better-with-annotated
# https://fastapi.tiangolo.com/tutorial/query-params-str-validations/#declare-more-metadata


# Dynamically import all routers
routers_dir = Path(__file__).parent / "routers"
for path in routers_dir.glob("*.py"):
    if path.name != "__init__.py":
        module_name = f"podium.routers.{path.stem}"
        module = importlib.import_module(module_name)
        # If the module has a router attribute, include it in the app
        if hasattr(module, "router"):
            app.include_router(getattr(module, "router"))

# @app.get("/sentry-debug")
# async def trigger_error():
#     division_by_zero = 1 / 0


def main():
    # Go to http://localhost:8000/docs to see the Swagger UI
    # or http://localhost:8000/redoc to see the specification
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
