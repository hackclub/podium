"""
One-time migration from Airtable to Postgres.
Idempotent: safe to run multiple times.

Run:
    doppler run --config dev -- python scripts/migrate_from_airtable.py
    doppler run --config prod -- python scripts/migrate_from_airtable.py
"""
import asyncio
from uuid import UUID

from podium.db.db import tables
from podium.db.models_ormar import (
    database,
    User,
    Event,
    Project,
    Vote,
    Referral,
)

# Maps Airtable record IDs to Postgres UUIDs
user_map: dict[str, UUID] = {}
event_map: dict[str, UUID] = {}
project_map: dict[str, UUID] = {}


async def migrate_users():
    print("Migrating users...")
    for record in tables["users"].all():
        fields = record["fields"]
        airtable_id = record["id"]

        existing = await User.objects.get_or_none(airtable_id=airtable_id)
        if existing:
            user_map[airtable_id] = existing.id
            continue

        user = await User.objects.create(
            airtable_id=airtable_id,
            email=fields.get("email", "").lower().strip(),
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
            dob=fields.get("dob"),
        )
        user_map[airtable_id] = user.id
    print(f"  {len(user_map)} users")


async def migrate_events():
    print("Migrating events...")
    for record in tables["events"].all():
        fields = record["fields"]
        airtable_id = record["id"]

        existing = await Event.objects.get_or_none(airtable_id=airtable_id)
        if existing:
            event_map[airtable_id] = existing.id
            continue

        owner_ids = fields.get("owner", [])
        if not owner_ids:
            print(f"  Skipping {airtable_id}: no owner")
            continue

        owner_uuid = user_map.get(owner_ids[0])
        if not owner_uuid:
            print(f"  Skipping {airtable_id}: owner not migrated")
            continue

        event = await Event.objects.create(
            airtable_id=airtable_id,
            name=fields.get("name", ""),
            slug=fields.get("slug", ""),
            description=fields.get("description", ""),
            join_code=fields.get("join_code", ""),
            votable=fields.get("votable", False),
            leaderboard_enabled=fields.get("leaderboard_enabled", False),
            demo_links_optional=fields.get("demo_links_optional", False),
            ysws_checks_enabled=fields.get("ysws_checks_enabled", False),
            feature_flags_csv=",".join(fields.get("feature_flags", [])),
            owner=owner_uuid,
        )
        event_map[airtable_id] = event.id
    print(f"  {len(event_map)} events")


async def migrate_event_attendees():
    """Add attendees to events using ormar's ManyToMany .add() method."""
    print("Migrating attendees...")
    count = 0
    for record in tables["events"].all():
        event_uuid = event_map.get(record["id"])
        if not event_uuid:
            continue

        event = await Event.objects.get(id=event_uuid)

        for user_airtable_id in record["fields"].get("attendees", []):
            user_uuid = user_map.get(user_airtable_id)
            if not user_uuid:
                continue

            user = await User.objects.get(id=user_uuid)

            # Check if already attending (ormar handles this gracefully)
            existing_attendees = await event.attendees.all()
            if user not in existing_attendees:
                await event.attendees.add(user)
                count += 1

    print(f"  {count} attendees")


async def migrate_projects():
    print("Migrating projects...")
    for record in tables["projects"].all():
        fields = record["fields"]
        airtable_id = record["id"]

        existing = await Project.objects.get_or_none(airtable_id=airtable_id)
        if existing:
            project_map[airtable_id] = existing.id
            continue

        owner_ids = fields.get("owner", [])
        event_ids = fields.get("event", [])
        if not owner_ids or not event_ids:
            print(f"  Skipping {airtable_id}: missing owner or event")
            continue

        owner_uuid = user_map.get(owner_ids[0])
        event_uuid = event_map.get(event_ids[0])
        if not owner_uuid or not event_uuid:
            print(f"  Skipping {airtable_id}: owner/event not migrated")
            continue

        project = await Project.objects.create(
            airtable_id=airtable_id,
            name=fields.get("name", ""),
            repo=fields.get("repo", ""),
            image_url=fields.get("image_url", ""),
            demo=fields.get("demo", ""),
            description=fields.get("description", ""),
            join_code=fields.get("join_code", ""),
            hours_spent=fields.get("hours_spent", 0),
            points=fields.get("points", 0),
            cached_auto_quality=fields.get("cached_auto_quality"),
            owner=owner_uuid,
            event=event_uuid,
        )
        project_map[airtable_id] = project.id
    print(f"  {len(project_map)} projects")


async def migrate_collaborators():
    """Add collaborators to projects using ormar's ManyToMany .add() method."""
    print("Migrating collaborators...")
    count = 0
    for record in tables["projects"].all():
        project_uuid = project_map.get(record["id"])
        if not project_uuid:
            continue

        project = await Project.objects.get(id=project_uuid)

        for user_airtable_id in record["fields"].get("collaborators", []):
            user_uuid = user_map.get(user_airtable_id)
            if not user_uuid:
                continue

            user = await User.objects.get(id=user_uuid)

            existing_collaborators = await project.collaborators.all()
            if user not in existing_collaborators:
                await project.collaborators.add(user)
                count += 1

    print(f"  {count} collaborators")


async def migrate_referrals():
    print("Migrating referrals...")
    count = 0
    for record in tables["referrals"].all():
        fields = record["fields"]
        airtable_id = record["id"]

        existing = await Referral.objects.get_or_none(airtable_id=airtable_id)
        if existing:
            continue

        user_ids = fields.get("user", [])
        event_ids = fields.get("event", [])
        if not user_ids or not event_ids:
            continue

        user_uuid = user_map.get(user_ids[0])
        event_uuid = event_map.get(event_ids[0])
        if not user_uuid or not event_uuid:
            continue

        await Referral.objects.create(
            airtable_id=airtable_id,
            content=fields.get("content", ""),
            user=user_uuid,
            event=event_uuid,
        )
        count += 1
    print(f"  {count} referrals")


async def migrate_votes():
    print("Migrating votes...")
    count = 0
    for record in tables["votes"].all():
        fields = record["fields"]
        airtable_id = record["id"]

        existing = await Vote.objects.get_or_none(airtable_id=airtable_id)
        if existing:
            continue

        voter_ids = fields.get("voter", [])
        project_ids = fields.get("project", [])
        event_ids = fields.get("event", [])
        if not all([voter_ids, project_ids, event_ids]):
            continue

        voter_uuid = user_map.get(voter_ids[0])
        project_uuid = project_map.get(project_ids[0])
        event_uuid = event_map.get(event_ids[0])
        if not all([voter_uuid, project_uuid, event_uuid]):
            continue

        await Vote.objects.create(
            airtable_id=airtable_id,
            voter=voter_uuid,
            project=project_uuid,
            event=event_uuid,
        )
        count += 1
    print(f"  {count} votes")


async def validate():
    print("\nValidation:")
    print(f"  Users: {await User.objects.count()}")
    print(f"  Events: {await Event.objects.count()}")
    print(f"  Projects: {await Project.objects.count()}")
    print(f"  Votes: {await Vote.objects.count()}")
    print(f"  Referrals: {await Referral.objects.count()}")


async def main():
    await database.connect()

    await migrate_users()
    await migrate_events()
    await migrate_event_attendees()
    await migrate_projects()
    await migrate_collaborators()
    await migrate_referrals()
    await migrate_votes()
    await validate()

    await database.disconnect()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
