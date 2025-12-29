"""
Database connection and session management for SQLModel.
"""

from collections.abc import AsyncGenerator, Sequence
from typing import TypeVar, cast

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from podium.config import settings

DATABASE_URL = settings.get("database_url", "")

engine = create_async_engine(DATABASE_URL, echo=False) if DATABASE_URL else None

async_session_factory = (
    async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    if engine
    else None
)


async def init_db():
    """Create all tables (for development/testing only - use Alembic in production)."""
    if engine:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    if not async_session_factory:
        raise RuntimeError("Database not configured. Set PODIUM_DATABASE_URL.")
    async with async_session_factory() as session:
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
    result = await session.execute(stmt)
    return cast(T | None, result.scalars().first())


async def scalar_all(session: AsyncSession, stmt: Select[tuple[T]]) -> list[T]:
    """Execute a select and return all model instances as a list."""
    result = await session.execute(stmt)
    return list(cast(Sequence[T], result.scalars().all()))
