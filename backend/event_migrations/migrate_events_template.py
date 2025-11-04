#!/usr/bin/env python3
"""
Generic event migration script template.
Migrate events from an external Airtable base into Podium.

Usage:
    1. Copy this template
    2. Configure SOURCE_* constants for your source base
    3. Configure EVENT_CONFIG for event-specific settings
    4. Run the script

The script will:
- Pull events from source Airtable base
- Create or find users based on POC email
- Create events in Podium with specified feature flags
- Support dry run mode and resumable migrations
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pyairtable import Api
from pyairtable.formulas import match
from podium import settings
from podium.db.user import UserSignupPayload
from podium.db.event import EventCreationPayload, Event
import re


# =============================================================================
# CONFIGURATION - UPDATE THESE FOR YOUR MIGRATION
# =============================================================================

# Source Airtable base configuration
SOURCE_BASE_ID = "appXXXXXXXXXXXXXX"  # External base to read from
SOURCE_EVENTS_TABLE_ID = "tblXXXXXXXXXXXXXX"  # Events table
SOURCE_EVENTS_VIEW_ID = "viwXXXXXXXXXXXXXX"  # Optional: specific view to pull

# Event-specific configuration
EVENT_CONFIG = {
    "feature_flag": "my-event",  # Feature flag to add to created events
    "votable": False,  # Default votable setting
    "leaderboard_enabled": False,  # Default leaderboard setting
    "demo_links_optional": True,  # Whether demo links are optional
}

# Field mappings from source to Podium
# Update these to match your source base field names
FIELD_MAPPINGS = {
    "event_name": "event_name",  # source -> podium
    "description": "description",
    "poc_email": "email",
    "poc_first_name": "first_name",
    "poc_last_name": "last_name",
    "poc_phone": "phone",
    "location": "location",  # Used in description generation
}

# Migration settings
TEST_RUN = True  # Set to False for actual migration
ENABLE_PER_EVENT_CONFIRMATION = False  # Set to True to confirm each event

# Production base IDs (from settings.toml)
PRODUCTION_BASE_ID = settings.airtable_base_id
PROD_EVENTS_TABLE_ID = settings.events_table_id
PROD_USERS_TABLE_ID = settings.users_table_id


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-")


def generate_join_code() -> str:
    """Generate a random 4-character join code."""
    import random
    import string

    return "".join(random.choices(string.ascii_uppercase + string.digits, k=4))


def airtable_link(record_id: str, base_id: str, table_id: str) -> str:
    """Create a clickable Airtable link for a record."""
    return f"https://airtable.com/{base_id}/{table_id}/{record_id}"


# =============================================================================
# DATA FETCHING
# =============================================================================


def get_source_events() -> List[Dict[str, Any]]:
    """Pull events from source Airtable base."""
    print("Pulling events from source base...")

    try:
        api = Api(api_key=settings.airtable_token)
        table = api.table(SOURCE_BASE_ID, SOURCE_EVENTS_TABLE_ID)

        # Use view if specified, otherwise get all
        if SOURCE_EVENTS_VIEW_ID:
            records = table.all(view=SOURCE_EVENTS_VIEW_ID)
        else:
            records = table.all()

        print(f"Found {len(records)} events")
        return records
    except Exception as e:
        print(f"Error pulling events: {e}")
        return []


def get_user_by_email(email: str) -> Optional[str]:
    """Get user record ID by email from production base."""
    try:
        api = Api(api_key=settings.airtable_token)
        users_table = api.table(PRODUCTION_BASE_ID, PROD_USERS_TABLE_ID)
        formula = match({"email": email})
        records = users_table.all(formula=formula)
        return records[0]["id"] if records else None
    except Exception as e:
        print(f"Error checking user: {e}")
        return None


def get_event_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """Get event by slug from production base."""
    try:
        api = Api(api_key=settings.airtable_token)
        events_table = api.table(PRODUCTION_BASE_ID, PROD_EVENTS_TABLE_ID)
        formula = match({"slug": slug})
        records = events_table.all(formula=formula)
        return records[0] if records else None
    except Exception as e:
        print(f"Error checking event: {e}")
        return None


# =============================================================================
# USER & EVENT CREATION
# =============================================================================


def create_or_find_user(source_event: Dict[str, Any]) -> Optional[str]:
    """Create or find user based on POC data from source event."""
    fields = source_event.get("fields", {})

    email = fields.get(FIELD_MAPPINGS["poc_email"], "").strip().lower()
    if not email:
        print("No email found for event")
        return None

    # Check if user exists
    existing_user_id = get_user_by_email(email)
    if existing_user_id:
        print(f"   ✅ Found existing user: {email}")
        return existing_user_id

    # Create new user
    print(f"   🆕 Creating new user: {email}")

    user_data = UserSignupPayload(
        email=email,
        first_name=fields.get(FIELD_MAPPINGS.get("poc_first_name", ""), "").strip(),
        last_name=fields.get(FIELD_MAPPINGS.get("poc_last_name", ""), "").strip(),
        display_name=fields.get(FIELD_MAPPINGS.get("poc_first_name", ""), "").strip(),
        phone=fields.get(FIELD_MAPPINGS.get("poc_phone", ""), "").strip(),
    )

    if TEST_RUN:
        print(f"   [DRY RUN] Would create user: {user_data.email}")
        return f"dry_run_user_{email.replace('@', '_').replace('.', '_')}"

    try:
        users_table = Api(api_key=settings.airtable_token).table(
            PRODUCTION_BASE_ID, PROD_USERS_TABLE_ID
        )
        record = users_table.create(user_data.model_dump())
        print(f"   ✅ Created user: {email}")
        return record["id"]
    except Exception as e:
        print(f"   ❌ Error creating user: {e}")
        return None


def create_event(source_event: Dict[str, Any], owner_id: str) -> Optional[str]:
    """Create an event in Podium production."""
    fields = source_event.get("fields", {})

    event_name = fields.get(FIELD_MAPPINGS["event_name"], "").strip()
    if not event_name:
        print("   ❌ No event name found")
        return None

    slug = slugify(event_name)

    # Check for existing event
    existing_event = get_event_by_slug(slug)
    if existing_event:
        print(f"   ⚠️  Event already exists with slug: {slug}")
        return "DUPLICATE_EVENT"

    # Generate description
    location = fields.get(FIELD_MAPPINGS.get("location", ""), "").strip()
    description = fields.get(FIELD_MAPPINGS.get("description", ""), "")
    if not description and location:
        description = f"Event in {location}"
    elif not description:
        description = event_name

    # Create event payload
    event_data = EventCreationPayload(
        name=event_name,
        description=description[:500],
        votable=EVENT_CONFIG["votable"],
        leaderboard_enabled=EVENT_CONFIG["leaderboard_enabled"],
        demo_links_optional=EVENT_CONFIG["demo_links_optional"],
    )

    # Add feature flag
    temp_event = Event(
        **event_data.model_dump(),
        id="",
        owner=[owner_id],
        slug=slug,
        feature_flags_csv=EVENT_CONFIG["feature_flag"],
    )

    if TEST_RUN:
        print(f"   [DRY RUN] Would create event: {event_name} (slug: {slug})")
        return f"dry_run_event_{slug}"

    try:
        events_table = Api(api_key=settings.airtable_token).table(
            PRODUCTION_BASE_ID, PROD_EVENTS_TABLE_ID
        )

        event_record = {
            **temp_event.model_dump(
                exclude={"id", "max_votes_per_user", "owned", "feature_flags_list"}
            ),
            "owner": [owner_id],
            "slug": slug,
            "join_code": generate_join_code(),
        }

        record = events_table.create(event_record)
        event_id = record["id"]
        print(f"   ✅ Created event: {event_name}")
        print(f"      Link: {airtable_link(event_id, PRODUCTION_BASE_ID, PROD_EVENTS_TABLE_ID)}")
        return event_id
    except Exception as e:
        print(f"   ❌ Error creating event: {e}")
        return None


# =============================================================================
# PROGRESS TRACKING
# =============================================================================


def save_progress(results: Dict[str, Any], filename: str):
    """Save migration progress to file."""
    os.makedirs("logs", exist_ok=True)
    filepath = os.path.join("logs", filename)
    with open(filepath, "w") as f:
        json.dump(results, f, indent=2)


def load_progress(filename: str) -> Optional[Dict[str, Any]]:
    """Load migration progress from file."""
    filepath = os.path.join("logs", filename)
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading progress: {e}")
        return None


# =============================================================================
# MAIN MIGRATION
# =============================================================================


def migrate_events(resume_from_file: str = None):
    """Main migration function."""
    print("=" * 80)
    print("EVENT MIGRATION")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if TEST_RUN else 'PRODUCTION'}")
    print(f"Feature Flag: {EVENT_CONFIG['feature_flag']}")
    print(f"Source Base: {SOURCE_BASE_ID}")
    print(f"Target Base: {PRODUCTION_BASE_ID}")
    print()

    # Load previous progress if resuming
    previous_progress = None
    if resume_from_file:
        previous_progress = load_progress(resume_from_file)
        if previous_progress:
            print(f"🔄 Resuming from: {resume_from_file}")
            print(f"   Previous: {previous_progress.get('successful', 0)} successful")

    # Pull source events
    source_events = get_source_events()
    if not source_events:
        print("No events found. Exiting.")
        return

    # Filter events with email
    events_to_migrate = [
        e for e in source_events if e.get("fields", {}).get(FIELD_MAPPINGS["poc_email"])
    ]

    if TEST_RUN:
        events_to_migrate = events_to_migrate[:1]

    print(f"Processing {len(events_to_migrate)} events")
    print()

    # Initialize results
    successful = []
    failed = []
    duplicates = []

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"migration_results_{EVENT_CONFIG['feature_flag']}_{timestamp}.json"

    for i, event in enumerate(events_to_migrate, 1):
        event_id = event.get("id", "unknown")
        event_name = event.get("fields", {}).get(FIELD_MAPPINGS["event_name"], "Unknown")

        print(f"{i}. {event_name}")

        # Create or find user
        owner_id = create_or_find_user(event)
        if not owner_id:
            failed.append({"event_id": event_id, "event_name": event_name, "error": "User creation failed"})
            continue

        # Create event
        podium_event_id = create_event(event, owner_id)
        if not podium_event_id:
            failed.append({"event_id": event_id, "event_name": event_name, "error": "Event creation failed"})
            continue
        elif podium_event_id == "DUPLICATE_EVENT":
            duplicates.append({"event_id": event_id, "event_name": event_name})
            continue

        successful.append({
            "source_event_id": event_id,
            "podium_event_id": podium_event_id,
            "event_name": event_name,
            "owner_id": owner_id,
        })

        # Save progress
        results = {
            "timestamp": datetime.now().isoformat(),
            "test_run": TEST_RUN,
            "feature_flag": EVENT_CONFIG["feature_flag"],
            "total_processed": i,
            "successful": len(successful),
            "failed": len(failed),
            "duplicates": len(duplicates),
            "successful_migrations": successful,
            "failed_migrations": failed,
            "duplicate_migrations": duplicates,
        }
        save_progress(results, results_file)
        print()

    # Print summary
    print("=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Duplicates: {len(duplicates)}")
    print(f"\nResults saved to: logs/{results_file}")


def main():
    """Entry point."""
    try:
        resume_file = None
        if len(sys.argv) > 2 and sys.argv[1] == "--resume":
            resume_file = sys.argv[2]

        migrate_events(resume_from_file=resume_file)
    except KeyboardInterrupt:
        print("\nMigration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
