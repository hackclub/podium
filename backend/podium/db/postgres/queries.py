"""
Reusable query helpers for common DB access patterns.

These functions centralize cross-cutting concerns like soft-delete filtering
so routers don't scatter `.where(Model.deleted_at.is_(None))` everywhere.
Add per-model helpers here as new models adopt soft-deletion or other patterns.

Usage:
    from podium.db.postgres.queries import get_active_event, list_active_events
"""

from uuid import UUID

from sqlalchemy.orm import Load
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from podium.db.postgres.base import scalar_one_or_none, scalar_all
from podium.db.postgres.event import Event


async def get_active_event(
    session: AsyncSession, event_id: UUID, *extra_loads: Load
) -> Event | None:
    """Fetch a non-deleted event by ID.

    Pass additional selectinload() calls to eagerly load relationships in the
    same query (avoids a second round-trip):
        event = await get_active_event(session, id, selectinload(Event.projects))
    """
    stmt = (
        select(Event)
        .where(Event.id == event_id, Event.deleted_at.is_(None))
        .options(*extra_loads)
    )
    return await scalar_one_or_none(session, stmt)


async def list_active_events(
    session: AsyncSession, *extra_loads: Load
) -> list[Event]:
    """Fetch all non-deleted events."""
    stmt = (
        select(Event)
        .where(Event.deleted_at.is_(None))
        .options(*extra_loads)
    )
    return await scalar_all(session, stmt)
