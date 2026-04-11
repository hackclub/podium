#!/usr/bin/env python3
"""
Run test-data cleanup directly (same logic as /events/test/cleanup endpoint).

Usage (from backend/):
  doppler run --config dev -- uv run python scripts/cleanup_test_data.py

This avoids needing the HTTP server to be running.
"""

import asyncio
import sys

# Add parent to path for imports
sys.path.insert(0, ".")

from podium.db.postgres.base import async_session_factory

# Import the existing cleanup function from the events router and reuse it so
# we don't duplicate SQL here.
from podium.routers.events import cleanup_test_data as router_cleanup


async def main():
    if not async_session_factory:
        print("Database not configured. Set PODIUM_DATABASE_URL.")
        sys.exit(1)

    print("\n🔧 Running test data cleanup...\n")

    async with async_session_factory() as session:
        # Reuse the router's cleanup implementation to avoid duplicating SQL.
        # The router function accepts a session (it normally gets it via Depends).
        await router_cleanup(session)

        # Also remove any admin+%@test.local test accounts/events created by E2E tooling
        from sqlmodel import text

        await session.execute(
            text("""
                DELETE FROM votes WHERE voter_id IN (
                    SELECT id FROM users WHERE email LIKE 'admin+%@test.local'
                )
            """)
        )
        await session.execute(
            text("""
                DELETE FROM votes WHERE project_id IN (
                    SELECT id FROM projects WHERE owner_id IN (
                        SELECT id FROM users WHERE email LIKE 'admin+%@test.local'
                    )
                )
            """)
        )
        await session.execute(
            text("""
                DELETE FROM project_collaborators WHERE user_id IN (
                    SELECT id FROM users WHERE email LIKE 'admin+%@test.local'
                )
            """)
        )
        await session.execute(
            text("""
                DELETE FROM projects WHERE owner_id IN (
                    SELECT id FROM users WHERE email LIKE 'admin+%@test.local'
                )
            """)
        )
        await session.execute(
            text("""
                DELETE FROM event_attendees WHERE user_id IN (
                    SELECT id FROM users WHERE email LIKE 'admin+%@test.local'
                )
            """)
        )
        await session.execute(
            text("""
                DELETE FROM events WHERE owner_id IN (
                    SELECT id FROM users WHERE email LIKE 'admin+%@test.local'
                )
            """)
        )
        await session.execute(
            text("""
                DELETE FROM referrals WHERE user_id IN (
                    SELECT id FROM users WHERE email LIKE 'admin+%@test.local'
                )
            """)
        )
        await session.execute(
            text("""
                DELETE FROM users WHERE email LIKE 'admin+%@test.local'
            """)
        )
        await session.commit()

    print("\n✅ Test data cleanup finished.\n")


if __name__ == "__main__":
    asyncio.run(main())
