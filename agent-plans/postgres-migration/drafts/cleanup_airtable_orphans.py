#!/usr/bin/env python3
"""
Find and optionally delete orphaned records in Airtable.

Orphaned records:
- Events with no owner
- Referrals pointing to deleted users or events
- Votes pointing to deleted users, projects, or events

Usage:
    doppler run --config prd -- uv run python scripts/cleanup_airtable_orphans.py
"""
import os
import tomllib

from pyairtable import Api

DRY_RUN = True  # Set to False to actually delete


def main():
    with open("settings.toml", "rb") as f:
        cfg = tomllib.load(f)["default"]

    api = Api(api_key=os.environ["PODIUM_AIRTABLE_TOKEN"])

    tables = {
        "users": api.table(cfg["airtable_base_id"], cfg["airtable_users_table_id"]),
        "events": api.table(cfg["airtable_base_id"], cfg["airtable_events_table_id"]),
        "projects": api.table(cfg["airtable_base_id"], cfg["airtable_projects_table_id"]),
        "votes": api.table(cfg["airtable_base_id"], cfg["airtable_votes_table_id"]),
        "referrals": api.table(cfg["airtable_base_id"], cfg["airtable_referrals_table_id"]),
    }

    print("Loading all records...")
    all_users = {r["id"] for r in tables["users"].all()}
    all_events = {r["id"] for r in tables["events"].all()}
    all_projects = {r["id"] for r in tables["projects"].all()}

    print(f"  Users: {len(all_users)}")
    print(f"  Events: {len(all_events)}")
    print(f"  Projects: {len(all_projects)}")

    orphaned = {"events": [], "referrals": [], "votes": []}

    # Find orphaned events (no owner)
    print("\nChecking events...")
    for rec in tables["events"].all():
        owner = rec["fields"].get("owner", [])
        if not owner:
            orphaned["events"].append(rec["id"])
            print(f"  Event {rec['id']} ({rec['fields'].get('name', 'unnamed')}): no owner")
        elif owner[0] not in all_users:
            orphaned["events"].append(rec["id"])
            print(f"  Event {rec['id']} ({rec['fields'].get('name', 'unnamed')}): owner {owner[0]} deleted")

    # Find orphaned referrals
    print("\nChecking referrals...")
    for rec in tables["referrals"].all():
        fields = rec["fields"]
        user_ids = fields.get("user", [])
        event_ids = fields.get("event", [])

        issues = []
        if not user_ids:
            issues.append("no user")
        elif user_ids[0] not in all_users:
            issues.append(f"user {user_ids[0]} deleted")
        if not event_ids:
            issues.append("no event")
        elif event_ids[0] not in all_events:
            issues.append(f"event {event_ids[0]} deleted")

        if issues:
            orphaned["referrals"].append(rec["id"])
            print(f"  Referral {rec['id']}: {', '.join(issues)}")

    # Find orphaned votes
    print("\nChecking votes...")
    for rec in tables["votes"].all():
        fields = rec["fields"]
        voter_ids = fields.get("voter", [])
        project_ids = fields.get("project", [])
        event_ids = fields.get("event", [])

        issues = []
        if not voter_ids:
            issues.append("no voter")
        elif voter_ids[0] not in all_users:
            issues.append(f"voter {voter_ids[0]} deleted")
        if not project_ids:
            issues.append("no project")
        elif project_ids[0] not in all_projects:
            issues.append(f"project {project_ids[0]} deleted")
        if not event_ids:
            issues.append("no event")
        elif event_ids[0] not in all_events:
            issues.append(f"event {event_ids[0]} deleted")

        if issues:
            orphaned["votes"].append(rec["id"])
            print(f"  Vote {rec['id']}: {', '.join(issues)}")

    # Summary and deletion
    print(f"\n{'='*50}")
    print("Summary of orphaned records:")
    print(f"  Events: {len(orphaned['events'])}")
    print(f"  Referrals: {len(orphaned['referrals'])}")
    print(f"  Votes: {len(orphaned['votes'])}")
    print(f"  DRY_RUN = {DRY_RUN}")

    if DRY_RUN:
        print("\nRe-run with DRY_RUN = False to delete orphaned records.")
    else:
        for table_name, record_ids in orphaned.items():
            for rid in record_ids:
                tables[table_name].delete(rid)
                print(f"  Deleted {table_name}: {rid}")
        print("\nOrphaned records deleted.")


if __name__ == "__main__":
    main()
