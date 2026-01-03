#!/usr/bin/env python3
"""
Clean up duplicate users in Airtable before migration to Postgres.

Deletes inactive duplicate users (no votes, no event attendance, no projects, 
no collaboration, no owned events). Keeps active users and logs cases where
multiple users with the same email are all active.

Usage:
    doppler run --config prd -- uv run python scripts/cleanup_airtable_users.py
"""
import os
import tomllib
from collections import defaultdict

from pyairtable import Api

DRY_RUN = False  # Set to False to actually delete


def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def main():
    # Load prod Airtable config
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

    print("Loading activity counts per user...")
    
    # Track detailed activity per user
    user_activity: dict[str, dict[str, int]] = defaultdict(lambda: {
        "events_attending": 0,
        "events_owned": 0,
        "projects_owned": 0,
        "projects_collab": 0,
        "votes": 0,
        "referrals": 0,
    })

    # Events: attendees + owner
    print("  Scanning events...")
    for rec in tables["events"].all():
        fields = rec.get("fields", {})
        for uid in fields.get("attendees", []):
            user_activity[uid]["events_attending"] += 1
        for uid in fields.get("owner", []):
            user_activity[uid]["events_owned"] += 1

    # Projects: owner + collaborators
    print("  Scanning projects...")
    for rec in tables["projects"].all():
        fields = rec.get("fields", {})
        for uid in fields.get("owner", []):
            user_activity[uid]["projects_owned"] += 1
        for uid in fields.get("collaborators", []):
            user_activity[uid]["projects_collab"] += 1

    # Votes: voter
    print("  Scanning votes...")
    for rec in tables["votes"].all():
        fields = rec.get("fields", {})
        for uid in fields.get("voter", []):
            user_activity[uid]["votes"] += 1

    # Referrals: user
    print("  Scanning referrals...")
    for rec in tables["referrals"].all():
        fields = rec.get("fields", {})
        for uid in fields.get("user", []):
            user_activity[uid]["referrals"] += 1

    active_ids = set(user_activity.keys())
    print(f"Found {len(active_ids)} active user IDs")

    # Group users by email
    print("Loading users and grouping by email...")
    users = list(tables["users"].all())
    by_email: dict[str, list[dict]] = defaultdict(list)

    for rec in users:
        fields = rec.get("fields", {})
        email = normalize_email(fields.get("email"))
        if email:
            by_email[email].append(rec)

    # Find duplicates
    dup_groups = {email: recs for email, recs in by_email.items() if len(recs) > 1}
    print(f"Found {len(dup_groups)} emails with duplicates")

    total_deleted = 0
    groups_with_multiple_actives = 0

    for email, records in dup_groups.items():
        actives = [r for r in records if r["id"] in active_ids]
        inactives = [r for r in records if r["id"] not in active_ids]

        # Choose primary: prefer active, then oldest by createdTime
        if actives:
            primary = sorted(actives, key=lambda r: r.get("createdTime", ""))[0]
        else:
            primary = sorted(records, key=lambda r: r.get("createdTime", ""))[0]

        primary_id = primary["id"]

        # Delete inactive duplicates (not the primary)
        inactive_to_delete = [r for r in inactives if r["id"] != primary_id]

        if len(actives) > 1:
            groups_with_multiple_actives += 1
            print(
                f"[MULTI-ACTIVE] {email}: {len(records)} total, "
                f"{len(actives)} active, keeping {primary_id}"
            )

        if inactive_to_delete:
            for rec in inactive_to_delete:
                rid = rec["id"]
                activity = user_activity.get(rid, {})
                total = sum(activity.values()) if activity else 0
                
                # Double-check: only delete if truly zero activity
                if total > 0:
                    print(f"  [SKIP] {rid} has activity: {activity}")
                    continue
                    
                total_deleted += 1
                if DRY_RUN:
                    print(f"  [DRY-RUN] Would delete: {rid} (activity: {activity})")
                else:
                    tables["users"].delete(rid)
                    print(f"  Deleted: {rid}")

    print(f"\n{'='*50}")
    print("Summary:")
    print(f"  Duplicate email groups: {len(dup_groups)}")
    print(f"  Groups with >1 active user: {groups_with_multiple_actives}")
    print(f"  Inactive duplicates deleted: {total_deleted}")
    print(f"  DRY_RUN = {DRY_RUN}")
    if DRY_RUN:
        print("\nRe-run with DRY_RUN = False to actually delete.")


if __name__ == "__main__":
    main()
