#!/usr/bin/env python3
"""
One-time migration from Airtable to PostgreSQL.

Idempotent: uses airtable_id to skip already-migrated records.
Safe to run multiple times.

Usage:
    doppler run --config dev -- uv run python scripts/migrate_from_airtable.py
    doppler run --config prod -- uv run python scripts/migrate_from_airtable.py
"""

import asyncio
import sys
from datetime import date
from uuid import UUID, uuid4

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession


def parse_date(value: str | None) -> date | None:
    """Parse a date string from Airtable (YYYY-MM-DD format)."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None

# Add parent to path for imports
sys.path.insert(0, ".")

from podium.db.db import tables, main as init_airtable  # noqa: E402
from podium.db.postgres.base import async_session_factory  # noqa: E402
from podium.db.postgres import (  # noqa: E402
    User,
    Event,
    Project,
    Vote,
    Referral,
    EventAttendeeLink,
    ProjectCollaboratorLink,
)


# Maps Airtable record IDs to Postgres UUIDs
user_map: dict[str, UUID] = {}
event_map: dict[str, UUID] = {}
project_map: dict[str, UUID] = {}


async def migrate_users(session: AsyncSession) -> None:
    """Migrate all users from Airtable to Postgres."""
    print("Migrating users...")
    created = 0
    skipped = 0

    for record in tables["users"].all():
        fields = record["fields"]
        airtable_id = record["id"]
        email = fields.get("email", "").lower().strip()

        # Check if already migrated by airtable_id
        existing = (await session.exec(
            select(User).where(User.airtable_id == airtable_id)
        )).first()
        if existing:
            user_map[airtable_id] = existing.id
            skipped += 1
            continue

        # Check if email already exists (from load tests or previous runs)
        existing_by_email = (await session.exec(
            select(User).where(User.email == email)
        )).first()
        if existing_by_email:
            # Update the existing record with airtable_id for future runs
            existing_by_email.airtable_id = airtable_id
            session.add(existing_by_email)
            user_map[airtable_id] = existing_by_email.id
            skipped += 1
            continue

        # Create new user
        user = User(
            id=uuid4(),
            airtable_id=airtable_id,
            email=email,
            display_name=fields.get("display_name", ""),
            first_name=fields.get("first_name", ""),
            last_name=fields.get("last_name", ""),
            phone=fields.get("phone", ""),
            street_1=fields.get("street_1", ""),
            street_2=fields.get("street_2", ""),
            city=fields.get("city", ""),
            state=fields.get("state", ""),
            zip_code=fields.get("zip_code", ""),
            country=fields.get("country", ""),
            dob=parse_date(fields.get("dob")),
        )
        session.add(user)
        await session.flush()  # Flush immediately to catch errors early
        user_map[airtable_id] = user.id
        created += 1

    await session.commit()
    print(f"  Users: {created} created, {skipped} skipped (already exist)")


async def migrate_events(session: AsyncSession) -> None:
    """Migrate all events from Airtable to Postgres."""
    print("Migrating events...")
    created = 0
    skipped = 0
    errors = 0

    for record in tables["events"].all():
        fields = record["fields"]
        airtable_id = record["id"]
        slug = fields.get("slug", "")
        join_code = fields.get("join_code", "")

        # Check if already migrated by airtable_id
        existing = (await session.exec(
            select(Event).where(Event.airtable_id == airtable_id)
        )).first()
        if existing:
            event_map[airtable_id] = existing.id
            skipped += 1
            continue

        # Check if slug or join_code already exists
        existing_by_unique = (await session.exec(
            select(Event).where((Event.slug == slug) | (Event.join_code == join_code))
        )).first()
        if existing_by_unique:
            existing_by_unique.airtable_id = airtable_id
            session.add(existing_by_unique)
            event_map[airtable_id] = existing_by_unique.id
            skipped += 1
            continue

        # Get owner UUID
        owner_ids = fields.get("owner", [])
        if not owner_ids:
            print(f"  Skipping event {airtable_id}: no owner")
            errors += 1
            continue

        owner_uuid = user_map.get(owner_ids[0])
        if not owner_uuid:
            print(f"  Skipping event {airtable_id}: owner {owner_ids[0]} not found")
            errors += 1
            continue

        # Create new event
        event = Event(
            id=uuid4(),
            airtable_id=airtable_id,
            name=fields.get("name", ""),
            slug=slug,
            description=fields.get("description", ""),
            join_code=join_code,
            votable=fields.get("votable", False),
            leaderboard_enabled=fields.get("leaderboard_enabled", False),
            demo_links_optional=fields.get("demo_links_optional", False),
            ysws_checks_enabled=fields.get("ysws_checks_enabled", False),
            feature_flags_csv=",".join(fields.get("feature_flags", [])),
            owner_id=owner_uuid,
        )
        session.add(event)
        await session.flush()
        event_map[airtable_id] = event.id
        created += 1

    await session.commit()
    print(f"  Events: {created} created, {skipped} skipped, {errors} errors")


async def migrate_attendees(session: AsyncSession) -> None:
    """Migrate event attendees (M2M relationship)."""
    print("Migrating attendees...")
    created = 0
    skipped = 0

    for record in tables["events"].all():
        event_airtable_id = record["id"]
        event_uuid = event_map.get(event_airtable_id)
        if not event_uuid:
            continue

        for user_airtable_id in record["fields"].get("attendees", []):
            user_uuid = user_map.get(user_airtable_id)
            if not user_uuid:
                continue

            # Check if link already exists
            existing = (await session.exec(
                select(EventAttendeeLink).where(
                    EventAttendeeLink.event_id == event_uuid,
                    EventAttendeeLink.user_id == user_uuid,
                )
            )).first()
            if existing:
                skipped += 1
                continue

            # Create link
            link = EventAttendeeLink(event_id=event_uuid, user_id=user_uuid)
            session.add(link)
            created += 1

    await session.commit()
    print(f"  Attendees: {created} created, {skipped} skipped")


async def migrate_projects(session: AsyncSession) -> None:
    """Migrate all projects from Airtable to Postgres."""
    print("Migrating projects...")
    created = 0
    skipped = 0
    errors = 0

    for record in tables["projects"].all():
        fields = record["fields"]
        airtable_id = record["id"]
        join_code = fields.get("join_code", "")

        # Check if already migrated by airtable_id
        existing = (await session.exec(
            select(Project).where(Project.airtable_id == airtable_id)
        )).first()
        if existing:
            project_map[airtable_id] = existing.id
            skipped += 1
            continue

        # Check if join_code already exists
        existing_by_code = (await session.exec(
            select(Project).where(Project.join_code == join_code)
        )).first()
        if existing_by_code:
            existing_by_code.airtable_id = airtable_id
            session.add(existing_by_code)
            project_map[airtable_id] = existing_by_code.id
            skipped += 1
            continue

        # Get owner and event UUIDs
        owner_ids = fields.get("owner", [])
        event_ids = fields.get("event", [])
        if not owner_ids or not event_ids:
            print(f"  Skipping project {airtable_id}: missing owner or event")
            errors += 1
            continue

        owner_uuid = user_map.get(owner_ids[0])
        event_uuid = event_map.get(event_ids[0])
        if not owner_uuid or not event_uuid:
            print(f"  Skipping project {airtable_id}: owner/event not migrated")
            errors += 1
            continue

        # Create new project
        project = Project(
            id=uuid4(),
            airtable_id=airtable_id,
            name=fields.get("name", ""),
            repo=fields.get("repo", ""),
            image_url=fields.get("image_url", ""),
            demo=fields.get("demo", ""),
            description=fields.get("description", ""),
            join_code=join_code,
            hours_spent=fields.get("hours_spent") or 0,
            points=fields.get("points") or 0,
            cached_auto_quality=fields.get("cached_auto_quality"),
            owner_id=owner_uuid,
            event_id=event_uuid,
        )
        session.add(project)
        await session.flush()
        project_map[airtable_id] = project.id
        created += 1

    await session.commit()
    print(f"  Projects: {created} created, {skipped} skipped, {errors} errors")


async def migrate_collaborators(session: AsyncSession) -> None:
    """Migrate project collaborators (M2M relationship)."""
    print("Migrating collaborators...")
    created = 0
    skipped = 0

    for record in tables["projects"].all():
        project_airtable_id = record["id"]
        project_uuid = project_map.get(project_airtable_id)
        if not project_uuid:
            continue

        for user_airtable_id in record["fields"].get("collaborators", []):
            user_uuid = user_map.get(user_airtable_id)
            if not user_uuid:
                continue

            # Check if link already exists
            existing = (await session.exec(
                select(ProjectCollaboratorLink).where(
                    ProjectCollaboratorLink.project_id == project_uuid,
                    ProjectCollaboratorLink.user_id == user_uuid,
                )
            )).first()
            if existing:
                skipped += 1
                continue

            # Create link
            link = ProjectCollaboratorLink(project_id=project_uuid, user_id=user_uuid)
            session.add(link)
            created += 1

    await session.commit()
    print(f"  Collaborators: {created} created, {skipped} skipped")


async def migrate_referrals(session: AsyncSession) -> None:
    """Migrate all referrals from Airtable to Postgres."""
    print("Migrating referrals...")
    created = 0
    skipped = 0
    errors = 0

    for record in tables["referrals"].all():
        fields = record["fields"]
        airtable_id = record["id"]

        # Check if already migrated
        existing = (await session.exec(
            select(Referral).where(Referral.airtable_id == airtable_id)
        )).first()
        if existing:
            skipped += 1
            continue

        # Get user and event UUIDs
        user_ids = fields.get("user", [])
        event_ids = fields.get("event", [])
        if not user_ids or not event_ids:
            errors += 1
            continue

        user_uuid = user_map.get(user_ids[0])
        event_uuid = event_map.get(event_ids[0])
        if not user_uuid or not event_uuid:
            errors += 1
            continue

        # Create new referral
        referral = Referral(
            id=uuid4(),
            airtable_id=airtable_id,
            content=fields.get("content", ""),
            user_id=user_uuid,
            event_id=event_uuid,
        )
        session.add(referral)
        created += 1

    await session.commit()
    print(f"  Referrals: {created} created, {skipped} skipped, {errors} errors")


async def migrate_votes(session: AsyncSession) -> None:
    """Migrate all votes from Airtable to Postgres."""
    print("Migrating votes...")
    created = 0
    skipped = 0
    errors = 0

    for record in tables["votes"].all():
        fields = record["fields"]
        airtable_id = record["id"]

        # Check if already migrated
        existing = (await session.exec(
            select(Vote).where(Vote.airtable_id == airtable_id)
        )).first()
        if existing:
            skipped += 1
            continue

        # Get all required UUIDs
        voter_ids = fields.get("voter", [])
        project_ids = fields.get("project", [])
        event_ids = fields.get("event", [])
        if not all([voter_ids, project_ids, event_ids]):
            errors += 1
            continue

        voter_uuid = user_map.get(voter_ids[0])
        project_uuid = project_map.get(project_ids[0])
        event_uuid = event_map.get(event_ids[0])
        if not all([voter_uuid, project_uuid, event_uuid]):
            errors += 1
            continue

        # Create new vote
        vote = Vote(
            id=uuid4(),
            airtable_id=airtable_id,
            voter_id=voter_uuid,
            project_id=project_uuid,
            event_id=event_uuid,
        )
        session.add(vote)
        created += 1

    await session.commit()
    print(f"  Votes: {created} created, {skipped} skipped, {errors} errors")


async def validate(session: AsyncSession) -> None:
    """Print row counts for validation."""
    print("\n--- Validation ---")

    # Postgres counts
    users = (await session.exec(select(User))).all()
    events = (await session.exec(select(Event))).all()
    projects = (await session.exec(select(Project))).all()
    votes = (await session.exec(select(Vote))).all()
    referrals = (await session.exec(select(Referral))).all()
    attendee_links = (await session.exec(select(EventAttendeeLink))).all()
    collab_links = (await session.exec(select(ProjectCollaboratorLink))).all()

    # Airtable counts
    at_users = len(list(tables["users"].all()))
    at_events = len(list(tables["events"].all()))
    at_projects = len(list(tables["projects"].all()))
    at_votes = len(list(tables["votes"].all()))
    at_referrals = len(list(tables["referrals"].all()))

    print(f"  Users:        {len(users):4} (Airtable: {at_users})")
    print(f"  Events:       {len(events):4} (Airtable: {at_events})")
    print(f"  Projects:     {len(projects):4} (Airtable: {at_projects})")
    print(f"  Votes:        {len(votes):4} (Airtable: {at_votes})")
    print(f"  Referrals:    {len(referrals):4} (Airtable: {at_referrals})")
    print(f"  Attendees:    {len(attendee_links):4} (M2M links)")
    print(f"  Collaborators:{len(collab_links):4} (M2M links)")


async def main() -> None:
    """Run the migration."""
    print("=" * 50)
    print("Airtable → PostgreSQL Migration")
    print("=" * 50)

    # Initialize Airtable connection
    print("\nConnecting to Airtable...")
    init_airtable()

    # Check Postgres connection
    if not async_session_factory:
        print("ERROR: Database not configured. Set PODIUM_DATABASE_URL.")
        return

    print("Connecting to PostgreSQL...")

    async with async_session_factory() as session:
        await migrate_users(session)
        await migrate_events(session)
        await migrate_attendees(session)
        await migrate_projects(session)
        await migrate_collaborators(session)
        await migrate_referrals(session)
        await migrate_votes(session)
        await validate(session)

    print("\n✓ Migration complete!")


if __name__ == "__main__":
    asyncio.run(main())
