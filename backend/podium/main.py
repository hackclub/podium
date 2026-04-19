import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import sentry_sdk
from fastapi import FastAPI
from fastapi_pagination import add_pagination
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from starlette.middleware.base import BaseHTTPMiddleware
from podium.limiter import limiter, get_user_or_ip_for_sentry

sentry_sdk.init(
    dsn=""
    if os.getenv("ENV_FOR_DYNACONF") == "development"
    else "https://489f4a109d07aeadfd13387bcd3197ab@o4508979744210944.ingest.de.sentry.io/4508979747553360",
    send_default_pii=True,
    traces_sample_rate=1.0,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    from podium.db.postgres import engine
    from podium.cache import init_redis, close_redis
    from podium.config import settings

    if engine:
        print("✓ PostgreSQL connection configured")
    else:
        print("⚠ PostgreSQL not configured. Set PODIUM_DATABASE_URL.")

    # Warn loudly if Turnstile is not configured outside of development —
    # unauthenticated endpoints will be unprotected without it.
    env = os.getenv("ENV_FOR_DYNACONF", "development")
    if env != "development" and not settings.get("turnstile_secret_key", ""):
        print("⚠ PODIUM_TURNSTILE_SECRET_KEY is not set. Turnstile verification is disabled — unauthenticated endpoints are unprotected.")

    await init_redis()

    yield

    await close_redis()


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class SentryUserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        user_key = get_user_or_ip_for_sentry(request)
        if "@" in user_key:
            sentry_sdk.set_user({"email": user_key})
        else:
            sentry_sdk.set_user({"ip_address": user_key})
        return await call_next(request)


app.add_middleware(SentryUserMiddleware)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dynamically import all routers from the routers directory
routers_dir = Path(__file__).parent / "routers"
for router_file in routers_dir.glob("*.py"):
    if router_file.stem != "__init__":
        module = __import__(
            f"podium.routers.{router_file.stem}", fromlist=["router"]
        )
        if hasattr(module, "router"):
            app.include_router(module.router)

add_pagination(app)


def main():
    import uvicorn

    uvicorn.run("podium.main:app", host="0.0.0.0", port=8000, reload=True)
