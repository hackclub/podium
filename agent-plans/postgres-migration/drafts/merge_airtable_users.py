#!/usr/bin/env python3
"""
Merge duplicate active users in Airtable.

For each email with 2+ active users:
1. Pick the user with more PII fields as primary
2. Reassign all activity (events, projects, votes, referrals) from duplicate to primary
3. Delete the duplicate user

Usage:
    doppler run --config prd -- uv run python scripts/merge_airtable_users.py
"""
import os
import tomllib
from collections import defaultdict

from pyairtable import Api

DRY_RUN = False  # Set to False to actually merge


def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def count_pii_fields(fields: dict) -> int:
    """Count how many PII fields are filled."""
    pii_fields = ['street_1', 'street_2', 'city', 'state', 'zip_code', 'country', 'phone', 'dob']
    return sum(1 for f in pii_fields if fields.get(f))


def replace_user_in_list(user_list: list[str], old_id: str, new_id: str, deleted_users: set[str]) -> list[str] | None:
    """Replace old_id with new_id in a list, avoiding duplicates. Returns None if no change."""
    if old_id not in user_list:
        return None
    
    result = [new_id if uid == old_id else uid for uid in user_list]
    # Remove duplicates and already-deleted users while preserving order
    seen = set()
    deduped = []
    for uid in result:
        if uid not in seen and uid not in deleted_users:
            seen.add(uid)
            deduped.append(uid)
    return deduped


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

    # Find duplicate users
    print("Loading users...")
    all_users = tables["users"].all()
    by_email: dict[str, list[dict]] = defaultdict(list)
    for u in all_users:
        email = normalize_email(u["fields"].get("email"))
        if email:
            by_email[email].append(u)

    duplicates = {e: recs for e, recs in by_email.items() if len(recs) > 1}
    print(f"Found {len(duplicates)} emails with duplicates")

    if not duplicates:
        print("No duplicates to merge!")
        return

    # Build merge plan: for each duplicate set, pick primary (most PII) and mark others for merge
    merge_plan: list[tuple[str, str, str]] = []  # (email, primary_id, duplicate_id)
    
    for email, users in duplicates.items():
        # Sort by PII count descending, then by createdTime ascending (older = tiebreaker)
        sorted_users = sorted(users, key=lambda u: (-count_pii_fields(u["fields"]), u.get("createdTime", "")))
        primary = sorted_users[0]
        for dup in sorted_users[1:]:
            merge_plan.append((email, primary["id"], dup["id"]))
            print(f"  {email}: keep {primary['id']} (pii={count_pii_fields(primary['fields'])}), merge {dup['id']} (pii={count_pii_fields(dup['fields'])})")

    print(f"\nMerge plan: {len(merge_plan)} users to merge into primaries")

    # Load all records that might reference users
    print("\nLoading events...")
    all_events = tables["events"].all()
    print(f"  {len(all_events)} events")

    print("Loading projects...")
    all_projects = tables["projects"].all()
    print(f"  {len(all_projects)} projects")

    print("Loading votes...")
    all_votes = tables["votes"].all()
    print(f"  {len(all_votes)} votes")

    print("Loading referrals...")
    all_referrals = tables["referrals"].all()
    print(f"  {len(all_referrals)} referrals")

    # Track already-deleted users to skip stale references
    deleted_users: set[str] = set()
    
    # Process each merge
    stats = {"events_updated": 0, "projects_updated": 0, "votes_updated": 0, "referrals_updated": 0, "users_deleted": 0}

    for email, primary_id, dup_id in merge_plan:
        print(f"\nMerging {dup_id} -> {primary_id} ({email})")

        # Update events: attendees and owner
        for event in all_events:
            fields = event["fields"]
            updates = {}

            attendees = fields.get("attendees", [])
            new_attendees = replace_user_in_list(attendees, dup_id, primary_id, deleted_users)
            if new_attendees is not None:
                updates["attendees"] = new_attendees
                print(f"  Event {event['id']}: attendees {dup_id} -> {primary_id}")

            owner = fields.get("owner", [])
            new_owner = replace_user_in_list(owner, dup_id, primary_id, deleted_users)
            if new_owner is not None:
                updates["owner"] = new_owner
                print(f"  Event {event['id']}: owner {dup_id} -> {primary_id}")

            if updates:
                stats["events_updated"] += 1
                if not DRY_RUN:
                    tables["events"].update(event["id"], updates)

        # Update projects: owner and collaborators
        for project in all_projects:
            fields = project["fields"]
            updates = {}

            owner = fields.get("owner", [])
            new_owner = replace_user_in_list(owner, dup_id, primary_id, deleted_users)
            if new_owner is not None:
                updates["owner"] = new_owner
                print(f"  Project {project['id']}: owner {dup_id} -> {primary_id}")

            collabs = fields.get("collaborators", [])
            new_collabs = replace_user_in_list(collabs, dup_id, primary_id, deleted_users)
            if new_collabs is not None:
                updates["collaborators"] = new_collabs
                print(f"  Project {project['id']}: collaborators {dup_id} -> {primary_id}")

            if updates:
                stats["projects_updated"] += 1
                if not DRY_RUN:
                    tables["projects"].update(project["id"], updates)

        # Update votes: voter
        for vote in all_votes:
            fields = vote["fields"]
            voter = fields.get("voter", [])
            new_voter = replace_user_in_list(voter, dup_id, primary_id, deleted_users)
            if new_voter is not None:
                stats["votes_updated"] += 1
                print(f"  Vote {vote['id']}: voter {dup_id} -> {primary_id}")
                if not DRY_RUN:
                    tables["votes"].update(vote["id"], {"voter": new_voter})

        # Update referrals: user
        for referral in all_referrals:
            fields = referral["fields"]
            user = fields.get("user", [])
            new_user = replace_user_in_list(user, dup_id, primary_id, deleted_users)
            if new_user is not None:
                stats["referrals_updated"] += 1
                print(f"  Referral {referral['id']}: user {dup_id} -> {primary_id}")
                if not DRY_RUN:
                    tables["referrals"].update(referral["id"], {"user": new_user})

        # Delete the duplicate user and track it
        stats["users_deleted"] += 1
        deleted_users.add(dup_id)
        print(f"  Deleting user {dup_id}")
        if not DRY_RUN:
            tables["users"].delete(dup_id)

    print(f"\n{'='*50}")
    print("Summary:")
    print(f"  Events updated: {stats['events_updated']}")
    print(f"  Projects updated: {stats['projects_updated']}")
    print(f"  Votes updated: {stats['votes_updated']}")
    print(f"  Referrals updated: {stats['referrals_updated']}")
    print(f"  Users deleted: {stats['users_deleted']}")
    print(f"  DRY_RUN = {DRY_RUN}")
    if DRY_RUN:
        print("\nRe-run with DRY_RUN = False to actually merge.")


if __name__ == "__main__":
    main()
