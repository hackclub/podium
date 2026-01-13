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
from tqdm import tqdm


def parse_date(value: str | None) -> date | None:
    """Parse a date string from Airtable (YYYY-MM-DD format)."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def truncate(value: str | None, max_length: int) -> str:
    """Truncate a string to max_length, handling None."""
    if not value:
        return ""
    return value[:max_length]

# Add parent to path for imports
sys.path.insert(0, ".")

from podium.db._airtable_deprecated.db import tables, main as init_airtable  # noqa: E402
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
    records = list(tables["users"].all())

    # Bulk fetch existing users (by airtable_id and email)
    existing_by_airtable = {
        u.airtable_id: u for u in (await session.exec(
            select(User).where(User.airtable_id.isnot(None))
        )).all()
    }
    existing_by_email = {
        u.email: u for u in (await session.exec(select(User))).all()
    }

    to_create: list[User] = []
    skipped = 0

    for record in tqdm(records, desc="Users", unit="rec"):
        fields = record["fields"]
        airtable_id = record["id"]
        email = fields.get("email", "").lower().strip()

        # Check if already migrated by airtable_id
        if airtable_id in existing_by_airtable:
            user_map[airtable_id] = existing_by_airtable[airtable_id].id
            skipped += 1
            continue

        # Check if email already exists (from load tests or previous runs)
        if email in existing_by_email:
            existing_user = existing_by_email[email]
            existing_user.airtable_id = airtable_id
            session.add(existing_user)
            user_map[airtable_id] = existing_user.id
            skipped += 1
            continue

        # Create new user (truncate fields to match DB constraints)
        user = User(
            id=uuid4(),
            airtable_id=airtable_id,
            email=email,
            display_name=truncate(fields.get("display_name"), 255),
            first_name=truncate(fields.get("first_name"), 50),
            last_name=truncate(fields.get("last_name"), 50),
            phone=truncate(fields.get("phone"), 20),
            street_1=truncate(fields.get("street_1"), 255),
            street_2=truncate(fields.get("street_2"), 255),
            city=truncate(fields.get("city"), 255),
            state=truncate(fields.get("state"), 255),
            zip_code=truncate(fields.get("zip_code"), 20),
            country=truncate(fields.get("country"), 100),
            dob=parse_date(fields.get("dob")),
        )
        to_create.append(user)
        user_map[airtable_id] = user.id

    session.add_all(to_create)
    await session.commit()
    print(f"  Users: {len(to_create)} created, {skipped} skipped (already exist)")


async def migrate_events(session: AsyncSession) -> None:
    """Migrate all events from Airtable to Postgres."""
    records = list(tables["events"].all())

    # Bulk fetch existing events
    existing_by_airtable = {
        e.airtable_id: e for e in (await session.exec(
            select(Event).where(Event.airtable_id.isnot(None))
        )).all()
    }
    all_events = (await session.exec(select(Event))).all()
    existing_by_slug = {e.slug: e for e in all_events}
    existing_by_code = {e.join_code: e for e in all_events}

    to_create: list[Event] = []
    skipped = 0
    errors = 0

    for record in tqdm(records, desc="Events", unit="rec"):
        fields = record["fields"]
        airtable_id = record["id"]
        slug = fields.get("slug", "")
        join_code = fields.get("join_code", "")

        # Check if already migrated by airtable_id
        if airtable_id in existing_by_airtable:
            event_map[airtable_id] = existing_by_airtable[airtable_id].id
            skipped += 1
            continue

        # Check if slug or join_code already exists
        existing_by_unique = existing_by_slug.get(slug) or existing_by_code.get(join_code)
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
        to_create.append(event)
        event_map[airtable_id] = event.id

    session.add_all(to_create)
    await session.commit()
    print(f"  Events: {len(to_create)} created, {skipped} skipped, {errors} errors")


async def migrate_attendees(session: AsyncSession) -> None:
    """Migrate event attendees (M2M relationship)."""
    records = list(tables["events"].all())

    # Bulk fetch existing links
    existing_links = {
        (link.event_id, link.user_id)
        for link in (await session.exec(select(EventAttendeeLink))).all()
    }

    to_create: list[EventAttendeeLink] = []
    skipped = 0

    for record in tqdm(records, desc="Attendees", unit="event"):
        event_airtable_id = record["id"]
        event_uuid = event_map.get(event_airtable_id)
        if not event_uuid:
            continue

        for user_airtable_id in record["fields"].get("attendees", []):
            user_uuid = user_map.get(user_airtable_id)
            if not user_uuid:
                continue

            # Check if link already exists
            if (event_uuid, user_uuid) in existing_links:
                skipped += 1
                continue

            # Create link
            link = EventAttendeeLink(event_id=event_uuid, user_id=user_uuid)
            to_create.append(link)
            existing_links.add((event_uuid, user_uuid))  # Prevent duplicates within batch

    session.add_all(to_create)
    await session.commit()
    print(f"  Attendees: {len(to_create)} created, {skipped} skipped")


async def migrate_projects(session: AsyncSession) -> None:
    """Migrate all projects from Airtable to Postgres."""
    records = list(tables["projects"].all())

    # Bulk fetch existing projects
    existing_by_airtable = {
        p.airtable_id: p for p in (await session.exec(
            select(Project).where(Project.airtable_id.isnot(None))
        )).all()
    }
    existing_by_code = {
        p.join_code: p for p in (await session.exec(select(Project))).all()
    }

    to_create: list[Project] = []
    skipped = 0
    errors = 0

    for record in tqdm(records, desc="Projects", unit="rec"):
        fields = record["fields"]
        airtable_id = record["id"]
        join_code = fields.get("join_code", "")

        # Check if already migrated by airtable_id
        if airtable_id in existing_by_airtable:
            project_map[airtable_id] = existing_by_airtable[airtable_id].id
            skipped += 1
            continue

        # Check if join_code already exists
        if join_code in existing_by_code:
            existing_proj = existing_by_code[join_code]
            existing_proj.airtable_id = airtable_id
            session.add(existing_proj)
            project_map[airtable_id] = existing_proj.id
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
        to_create.append(project)
        project_map[airtable_id] = project.id

    session.add_all(to_create)
    await session.commit()
    print(f"  Projects: {len(to_create)} created, {skipped} skipped, {errors} errors")


async def migrate_collaborators(session: AsyncSession) -> None:
    """Migrate project collaborators (M2M relationship)."""
    records = list(tables["projects"].all())

    # Bulk fetch existing links
    existing_links = {
        (link.project_id, link.user_id)
        for link in (await session.exec(select(ProjectCollaboratorLink))).all()
    }

    to_create: list[ProjectCollaboratorLink] = []
    skipped = 0

    for record in tqdm(records, desc="Collaborators", unit="proj"):
        project_airtable_id = record["id"]
        project_uuid = project_map.get(project_airtable_id)
        if not project_uuid:
            continue

        for user_airtable_id in record["fields"].get("collaborators", []):
            user_uuid = user_map.get(user_airtable_id)
            if not user_uuid:
                continue

            # Check if link already exists
            if (project_uuid, user_uuid) in existing_links:
                skipped += 1
                continue

            # Create link
            link = ProjectCollaboratorLink(project_id=project_uuid, user_id=user_uuid)
            to_create.append(link)
            existing_links.add((project_uuid, user_uuid))  # Prevent duplicates within batch

    session.add_all(to_create)
    await session.commit()
    print(f"  Collaborators: {len(to_create)} created, {skipped} skipped")


async def migrate_referrals(session: AsyncSession) -> None:
    """Migrate all referrals from Airtable to Postgres."""
    records = list(tables["referrals"].all())

    # Bulk fetch existing referrals
    existing_airtable_ids = {
        r.airtable_id for r in (await session.exec(
            select(Referral).where(Referral.airtable_id.isnot(None))
        )).all()
    }

    to_create: list[Referral] = []
    skipped = 0
    errors = 0

    for record in tqdm(records, desc="Referrals", unit="rec"):
        fields = record["fields"]
        airtable_id = record["id"]

        # Check if already migrated
        if airtable_id in existing_airtable_ids:
            skipped += 1
            continue

        # Get user and event UUIDs
        user_ids = fields.get("user", [])
        event_ids = fields.get("event", [])
        if not user_ids or not event_ids:
            tqdm.write(f"  [SKIP] Referral {airtable_id}: missing user={user_ids} or event={event_ids}")
            errors += 1
            continue

        user_uuid = user_map.get(user_ids[0])
        event_uuid = event_map.get(event_ids[0])
        if not user_uuid or not event_uuid:
            missing = []
            if not user_uuid:
                missing.append(f"user {user_ids[0]}")
            if not event_uuid:
                missing.append(f"event {event_ids[0]}")
            tqdm.write(f"  [SKIP] Referral {airtable_id}: {', '.join(missing)} not migrated")
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
        to_create.append(referral)

    session.add_all(to_create)
    await session.commit()
    print(f"  Referrals: {len(to_create)} created, {skipped} skipped, {errors} errors")


async def migrate_votes(session: AsyncSession) -> None:
    """Migrate all votes from Airtable to Postgres."""
    records = list(tables["votes"].all())

    # Bulk fetch existing votes
    all_votes = (await session.exec(select(Vote))).all()
    existing_airtable_ids = {v.airtable_id for v in all_votes if v.airtable_id}
    existing_voter_project = {(v.voter_id, v.project_id) for v in all_votes}

    to_create: list[Vote] = []
    skipped = 0
    errors = 0

    for record in tqdm(records, desc="Votes", unit="rec"):
        fields = record["fields"]
        airtable_id = record["id"]

        # Check if already migrated
        if airtable_id in existing_airtable_ids:
            skipped += 1
            continue

        # Get all required UUIDs
        voter_ids = fields.get("voter", [])
        project_ids = fields.get("project", [])
        event_ids = fields.get("event", [])
        if not all([voter_ids, project_ids, event_ids]):
            tqdm.write(f"  [SKIP] Vote {airtable_id}: missing voter={voter_ids}, project={project_ids}, event={event_ids}")
            errors += 1
            continue

        voter_uuid = user_map.get(voter_ids[0])
        project_uuid = project_map.get(project_ids[0])
        event_uuid = event_map.get(event_ids[0])
        if not all([voter_uuid, project_uuid, event_uuid]):
            missing = []
            if not voter_uuid:
                missing.append(f"voter {voter_ids[0]}")
            if not project_uuid:
                missing.append(f"project {project_ids[0]}")
            if not event_uuid:
                missing.append(f"event {event_ids[0]}")
            tqdm.write(f"  [SKIP] Vote {airtable_id}: {', '.join(missing)} not migrated")
            errors += 1
            continue

        # Check for duplicate vote (same voter + project)
        if (voter_uuid, project_uuid) in existing_voter_project:
            skipped += 1
            continue

        # Create new vote
        vote = Vote(
            id=uuid4(),
            airtable_id=airtable_id,
            voter_id=voter_uuid,
            project_id=project_uuid,
            event_id=event_uuid,
        )
        to_create.append(vote)
        existing_voter_project.add((voter_uuid, project_uuid))  # Prevent duplicates within batch

    session.add_all(to_create)
    await session.commit()
    print(f"  Votes: {len(to_create)} created, {skipped} skipped, {errors} errors")


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
