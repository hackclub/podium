"""
Database connection and session management for SQLModel.

Two engines are provided:
  - engine / get_session()    — read-write (always uses database_url)
  - ro_engine / get_ro_session() — read-only (uses database_url_ro in prod,
                                   falls back to database_url in dev)

In development (database_url_ro not set), both point to the same instance.
"""

from collections.abc import AsyncGenerator, Sequence
from typing import TypeVar, cast
import ssl
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from podium.config import settings

DATABASE_URL = settings.get("database_url", "")
DATABASE_URL_RO = settings.get("database_url_ro", "") or DATABASE_URL  # fall back to rw in dev


def _build_async_engine(url: str):
    """Create an async engine while normalizing SSL params for asyncpg."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)

    # asyncpg does not accept sslmode/sslrootcert as direct kwargs.
    sslmode = qs.pop("sslmode", [None])[-1]
    qs.pop("sslrootcert", None)

    normalized_url = urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))

    connect_args: dict = {}
    if sslmode == "require" or (parsed.hostname and parsed.hostname not in {"localhost", "127.0.0.1"}):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx

    return create_async_engine(normalized_url, echo=False, connect_args=connect_args)

# Read-write engine — use for all mutations
engine = _build_async_engine(DATABASE_URL) if DATABASE_URL else None

# Read-only engine — use for public read endpoints (leaderboard, project listing, etc.)
ro_engine = _build_async_engine(DATABASE_URL_RO) if DATABASE_URL_RO else engine

async_session_factory = (
    async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    if engine
    else None
)

ro_session_factory = (
    async_sessionmaker(ro_engine, class_=AsyncSession, expire_on_commit=False)
    if ro_engine
    else None
)


async def init_db():
    """Create all tables (for development/testing only - use Alembic in production)."""
    if engine:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency: read-write database session. Use for any endpoint that writes data."""
    if not async_session_factory:
        raise RuntimeError("Database not configured. Set PODIUM_DATABASE_URL.")
    async with async_session_factory() as session:
        yield session


async def get_ro_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency: read-only database session. Use for public read endpoints.
    In dev (no database_url_ro set), this is the same as get_session()."""
    factory = ro_session_factory or async_session_factory
    if not factory:
        raise RuntimeError("Database not configured. Set PODIUM_DATABASE_URL.")
    async with factory() as session:
        yield session


# =============================================================================
# Typed Query Helpers
#
# SQLAlchemy's execute() returns Row tuples, e.g. (User(...),). Calling
# .scalars() extracts the model object directly. These helpers wrap that
# pattern with proper typing, since execute() returns Result[Any].
#
# For primary key lookups, prefer session.get(Model, id) instead.
# =============================================================================

T = TypeVar("T", bound=SQLModel)


async def scalar_one_or_none(session: AsyncSession, stmt: Select[tuple[T]]) -> T | None:
    """Execute a select and return the first model instance, or None if not found."""
    result = await session.exec(stmt)  # type: ignore[arg-type]
    return cast(T | None, result.first())


async def scalar_all(session: AsyncSession, stmt: Select[tuple[T]]) -> list[T]:
    """Execute a select and return all model instances as a list."""
    result = await session.exec(stmt)  # type: ignore[arg-type]
    return list(cast(Sequence[T], result.all()))
