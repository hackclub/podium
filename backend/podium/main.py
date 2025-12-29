import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sentry_sdk.init(
    dsn=""
    if os.getenv("ENV_FOR_DYNACONF") == "development"
    else "https://489f4a109d07aeadfd13387bcd3197ab@o4508979744210944.ingest.de.sentry.io/4508979747553360",
    send_default_pii=True,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    from podium.db.postgres import engine

    if engine:
        print("✓ PostgreSQL connection configured")
    else:
        print("⚠ PostgreSQL not configured. Set PODIUM_DATABASE_URL.")

    yield


app = FastAPI(lifespan=lifespan)

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


def main():
    import uvicorn

    uvicorn.run("podium.main:app", host="0.0.0.0", port=8000, reload=True)
