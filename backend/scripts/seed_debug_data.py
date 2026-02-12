#!/usr/bin/env python3
"""
Seed script for creating debug/test data.

Creates:
- A flagship event with angad+debug@hackclub.com as owner
- A second user angad+debug2@hackclub.com attending the event
- A valid project submitted by the second user

Usage:
    cd backend
    doppler run --config dev -- uv run python scripts/seed_debug_data.py
"""

import asyncio
import sys
from secrets import token_urlsafe

# Add parent to path for imports
sys.path.insert(0, ".")

from sqlmodel import select
from podium.db.postgres.base import async_session_factory, scalar_one_or_none
from podium.db.postgres.user import User
from podium.db.postgres.event import Event
from podium.db.postgres.project import Project
from podium.db.postgres.links import EventAttendeeLink

from podium.config import settings as podium_settings


async def get_or_create_user(session, email: str, first_name: str, last_name: str) -> User:
    """Get existing user or create new one."""
    stmt = select(User).where(User.email == email)
    user = await scalar_one_or_none(session, stmt)
    
    if user:
        print(f"✓ User {email} already exists (ID: {user.id})")
        return user
    
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        display_name=f"{first_name} {last_name}",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    print(f"✓ Created user {email} (ID: {user.id})")
    return user


async def create_flagship_event(session, owner: User) -> Event:
    """Create a flagship event."""
    # Check if event already exists
    stmt = select(Event).where(Event.slug == "flagship-debug")
    existing = await scalar_one_or_none(session, stmt)
    
    if existing:
        print(f"✓ Event 'flagship-debug' already exists (ID: {existing.id})")
        return existing
    
    event = Event(
        name="Flagship Debug Event",
        slug="flagship-debug",
        description="A debug flagship event for testing purposes",
        votable=True,
        leaderboard_enabled=True,
        demo_links_optional=False,
        ysws_checks_enabled=False,
        feature_flags_csv=podium_settings.active_event_series,
        owner_id=owner.id,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    print(f"✓ Created flagship event '{event.name}' (ID: {event.id})")
    return event


async def add_attendee(session, event: Event, user: User) -> None:
    """Add user as attendee to event."""
    # Check if already attending
    stmt = select(EventAttendeeLink).where(
        EventAttendeeLink.event_id == event.id,
        EventAttendeeLink.user_id == user.id
    )
    result = await session.exec(stmt)
    existing = result.first()
    
    if existing:
        print(f"✓ User {user.email} is already attending the event")
        return
    
    link = EventAttendeeLink(
        event_id=event.id,
        user_id=user.id,
    )
    session.add(link)
    await session.commit()
    print(f"✓ Added {user.email} as attendee to event")


async def create_project(session, owner: User, event: Event) -> Project:
    """Create a project for the user."""
    # Check if project already exists
    stmt = select(Project).where(
        Project.owner_id == owner.id,
        Project.event_id == event.id
    )
    result = await session.exec(stmt)
    existing = result.first()
    
    if existing:
        print(f"✓ Project '{existing.name}' already exists for {owner.email} (ID: {existing.id})")
        return existing
    
    project = Project(
        name="Pixel Dash",
        repo="https://github.com/yourname/gamename",
        image_url="https://hackclub.com/stickers/logo.png",
        demo="https://vempr.itch.io/pixeldash",
        description="A fast-paced pixel art platformer game where you dash through challenging levels. Built during the flagship hackathon!",
        join_code=token_urlsafe(8),
        hours_spent=12,
        owner_id=owner.id,
        event_id=event.id,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    print(f"✓ Created project '{project.name}' (ID: {project.id})")
    print(f"  Project join code: {project.join_code}")
    return project


async def main():
    """Main seed script."""
    if not async_session_factory:
        print("❌ Database not configured. Set PODIUM_DATABASE_URL.")
        sys.exit(1)
    
    print("\n🌱 Starting seed script...\n")
    
    async with async_session_factory() as session:
        # Create or get owner user
        owner = await get_or_create_user(
            session,
            email="angad+debug@hackclub.com",
            first_name="Angad",
            last_name="Debug"
        )
        
        # Create flagship event
        event = await create_flagship_event(session, owner)
        
        # Create or get second user
        attendee = await get_or_create_user(
            session,
            email="angad+debug2@hackclub.com",
            first_name="Angad",
            last_name="Debug2"
        )
        
        # Add second user as attendee
        await add_attendee(session, event, attendee)
        
        # Create project for second user
        project = await create_project(session, attendee, event)
    
    print("\n✅ Seed script completed successfully!\n")
    print("Summary:")
    print(f"  Event: {event.name} (slug: {event.slug})")
    print(f"  Owner: {owner.email}")
    print(f"  Attendee: {attendee.email}")
    print(f"  Project: {project.name}")
    print(f"\nProject join code: {project.join_code}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
