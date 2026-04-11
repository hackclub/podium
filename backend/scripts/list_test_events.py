#!/usr/bin/env python3
"""
List events and owners to help debug leftover test events.

Usage (from backend/):
  doppler run --config dev -- uv run python scripts/list_test_events.py
"""

import asyncio
import sys

sys.path.insert(0, ".")
from sqlmodel import select
from podium.db.postgres.base import async_session_factory
from podium.db.postgres import Event, User


async def main():
    if not async_session_factory:
        print("DB not configured")
        return
    async with async_session_factory() as session:
        result = await session.exec(select(Event))
        events = result.all()
        print(f"Found {len(events)} events")
        for e in events:
            owner = None
            if e.owner_id:
                owner = await session.get(User, e.owner_id)
            print(
                f"- {e.name!r} slug={e.slug} id={e.id} owner_email={(owner.email if owner else None)} phase={e.phase}"
            )


if __name__ == "__main__":
    asyncio.run(main())
