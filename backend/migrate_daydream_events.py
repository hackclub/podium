#!/usr/bin/env python3
"""
Migration script to pull Daydream events from Airtable and create them in Podium.
This script will:
1. Pull events from the Daydream Airtable base
2. Create or find users based on POC email
3. Create events in Podium production with daydream tag
4. Support dry run mode for testing
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pyairtable import Api
from podium import settings
from podium.db.user import UserSignupPayload
from podium.db.event import EventCreationPayload, Event
import re


# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# Migration settings
TEST_RUN = False  # Set to False for actual migration
ENABLE_PER_EVENT_CONFIRMATION = False  # Set to False to skip per-event confirmations

# Airtable configuration
DAYDREAM_BASE_ID = "apppg7RHZv6feM66l"
DAYDREAM_TABLE_ID = "tblFkqWvQKUIXYjMK"
DAYDREAM_ATTENDEES_TABLE_ID = "tbllZB3SJWitK6JRP"
DAYDREAM_ATTENDEES_VIEW_ID = "viwQIJ5B839y7bxdQ"
PRODUCTION_BASE_ID = "appmCFCuFmxkvO1zc"  # Production base ID from settings.toml

# Production table IDs (from settings.toml default section)
PROD_EVENTS_TABLE_ID = "tblf7gxCB41f6PaPf"
PROD_USERS_TABLE_ID = "tblwoiggOeX0s6nyG"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def slugify(text: str) -> str:
    """Simple slugify function to convert text to URL-friendly format."""
    # Convert to lowercase and replace spaces with hyphens
    text = text.lower().strip()
    # Remove special characters except hyphens and alphanumeric
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    # Replace spaces and multiple hyphens with single hyphen
    text = re.sub(r'[\s-]+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text


def airtable_link(record_id: str, base_id: str, table_id: str) -> str:
    """Create a clickable Airtable link for a record ID."""
    return f"https://airtable.com/{base_id}/{table_id}/{record_id}"


def format_record_id(record_id: str, base_id: str, table_id: str, label: str = None) -> str:
    """Format a record ID as a clickable link with optional label."""
    link = airtable_link(record_id, base_id, table_id)
    display_text = label or record_id
    return f"{display_text} -> {link}"




def get_daydream_events() -> List[Dict[str, Any]]:
    """Pull Daydream events from Airtable using the specific view."""
    print("Pulling Daydream events from Airtable...")
    
    try:
        api = Api(api_key=settings.airtable_token)
        table = api.table(DAYDREAM_BASE_ID, DAYDREAM_TABLE_ID)
        
        # Get records from the specific Daydream view
        view_id = "viwqnirjV2VES9d8o"
        records = table.all(view=view_id)
        print(f"Found {len(records)} Daydream events from view {view_id}")
        
        return records
    except Exception as e:
        print(f"Error pulling Daydream events: {e}")
        return []


def get_daydream_attendees() -> List[Dict[str, Any]]:
    """Pull Daydream attendees from Airtable using the specific view."""
    print("Pulling Daydream attendees from Airtable...")
    
    try:
        api = Api(api_key=settings.airtable_token)
        table = api.table(DAYDREAM_BASE_ID, DAYDREAM_ATTENDEES_TABLE_ID)
        
        # Get records from the specific Daydream attendees view
        records = table.all(view=DAYDREAM_ATTENDEES_VIEW_ID)
        print(f"Found {len(records)} Daydream attendees from view {DAYDREAM_ATTENDEES_VIEW_ID}")
        
        return records
    except Exception as e:
        print(f"Error pulling Daydream attendees: {e}")
        return []


def get_user_record_id_by_email_production(email: str) -> Optional[str]:
    """Get user record ID by email from production base."""
    try:
        api = Api(api_key=settings.airtable_token)
        users_table = api.table(PRODUCTION_BASE_ID, PROD_USERS_TABLE_ID)
        
        from pyairtable.formulas import match
        formula = match({"email": email})
        records = users_table.all(formula=formula)
        return records[0]["id"] if records else None
    except Exception as e:
        print(f"Error checking user existence: {e}")
        return None


def get_all_users_by_email_production(email: str) -> List[Dict[str, Any]]:
    """Get all user records by email from production base (to check for duplicates)."""
    try:
        api = Api(api_key=settings.airtable_token)
        users_table = api.table(PRODUCTION_BASE_ID, PROD_USERS_TABLE_ID)
        
        from pyairtable.formulas import match
        formula = match({"email": email})
        records = users_table.all(formula=formula)
        return records
    except Exception as e:
        print(f"Error checking user existence: {e}")
        return []


def get_event_by_name_production(event_name: str) -> Optional[Dict[str, Any]]:
    """Get event by name from production base."""
    try:
        api = Api(api_key=settings.airtable_token)
        events_table = api.table(PRODUCTION_BASE_ID, PROD_EVENTS_TABLE_ID)
        
        from pyairtable.formulas import match
        formula = match({"name": event_name})
        records = events_table.all(formula=formula)
        return records[0] if records else None
    except Exception as e:
        print(f"Error checking event by name: {e}")
        return None


def get_event_by_slug_production(slug: str) -> Optional[Dict[str, Any]]:
    """Get event by slug from production base."""
    try:
        api = Api(api_key=settings.airtable_token)
        events_table = api.table(PRODUCTION_BASE_ID, PROD_EVENTS_TABLE_ID)
        
        from pyairtable.formulas import match
        formula = match({"slug": slug})
        records = events_table.all(formula=formula)
        return records[0] if records else None
    except Exception as e:
        print(f"Error checking event by slug: {e}")
        return None


def check_event_exists(event_name: str, slug: str) -> Dict[str, Any]:
    """Check if event exists by name or slug and return details."""
    result = {
        "exists": False,
        "by_name": False,
        "by_slug": False,
        "name_match": None,
        "slug_match": None
    }
    
    # Check by name
    name_match = get_event_by_name_production(event_name)
    if name_match:
        result["exists"] = True
        result["by_name"] = True
        result["name_match"] = name_match
    
    # Check by slug
    slug_match = get_event_by_slug_production(slug)
    if slug_match:
        result["exists"] = True
        result["by_slug"] = True
        result["slug_match"] = slug_match
    
    return result


def create_display_name(first_name: str, last_name: str, preferred_name: str = "") -> str:
    """Create display name following the rules: preferred_name or first_name + last_initial."""
    if preferred_name and preferred_name.strip():
        return preferred_name.strip()
    
    if first_name and last_name:
        last_initial = last_name.strip()[0].upper() if last_name.strip() else ""
        return f"{first_name.strip()} {last_initial}."
    
    return first_name.strip() if first_name else ""


def get_phone_value(phone: str) -> str:
    """Get phone value as-is from Daydream data."""
    return phone.strip() if phone else ""


def create_or_find_attendee_user(daydream_attendee: Dict[str, Any]) -> Optional[str]:
    """Create or find user based on attendee data from Daydream."""
    fields = daydream_attendee.get("fields", {})
    
    email = fields.get("email", "").strip().lower()
    if not email:
        print(f"No email found for attendee {daydream_attendee.get('id', 'unknown')}")
        return None
    
    # Check for duplicate users
    existing_users = get_all_users_by_email_production(email)
    
    if len(existing_users) > 1:
        return "DUPLICATE_EMAIL"
    elif len(existing_users) == 1:
        user_id = existing_users[0]["id"]
        return user_id
    
    # Create new user
    
    # Parse date of birth
    dob_str = fields.get("dob", "")
    dob = None
    if dob_str:
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"Invalid date format for DOB: {dob_str}")
    
    # Create display name
    first_name = fields.get("first_name", "").strip()
    last_name = fields.get("last_name", "").strip()
    preferred_name = fields.get("preferred_name", "").strip()
    display_name = create_display_name(first_name, last_name, preferred_name)
    
    # Create user payload
    user_data = UserSignupPayload(
        email=email,
        first_name=first_name,
        last_name=last_name,
        display_name=display_name,
        phone=get_phone_value(fields.get("phone", "")),
        street_1=fields.get("address_1", "").strip(),
        street_2=fields.get("address_2", "").strip(),
        city=fields.get("city", "").strip(),
        state=fields.get("state", "").strip(),
        zip_code=fields.get("zip_code", "").strip(),
        country=fields.get("country", "").strip(),
        dob=dob
    )
    
    if TEST_RUN:
        return f"dry_run_attendee_user_{email.replace('@', '_').replace('.', '_')}"
    
    try:
        # Create user in production Airtable
        users_table = Api(api_key=settings.airtable_token).table(PRODUCTION_BASE_ID, PROD_USERS_TABLE_ID)
        record = users_table.create(user_data.model_dump())
        user_id = record["id"]
        return user_id
    except Exception as e:
        print(f"   ❌ Error creating attendee user {email}: {e}")
        return None


def create_or_find_user(daydream_event: Dict[str, Any]) -> Optional[str]:
    """Create or find user based on POC data from Daydream event."""
    fields = daydream_event.get("fields", {})
    
    email = fields.get("email", "").strip().lower()
    if not email:
        print(f"No email found for event {daydream_event.get('id', 'unknown')}")
        return None
    
    # Check if user already exists in production
    existing_user_id = get_user_record_id_by_email_production(email)
    if existing_user_id:
        return existing_user_id
    
    # Create new user
    print(f"Creating new user for {email}")
    
    # Parse date of birth
    dob_str = fields.get("poc_dob", "")
    dob = None
    if dob_str:
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"Invalid date format for DOB: {dob_str}")
    
    # Create user payload
    user_data = UserSignupPayload(
        email=email,
        first_name=fields.get("poc_first_name", "").strip(),
        last_name=fields.get("poc_last_name", "").strip(),
        display_name=fields.get("poc_preferred_name", "").strip() or fields.get("poc_first_name", "").strip(),
        phone=get_phone_value(fields.get("poc_phone", "")),  # Use phone as-is if available
        street_1=fields.get("street_address", "").strip(),
        street_2="",
        city=fields.get("city", "").strip(),
        state=fields.get("state", "").strip(),
        zip_code=fields.get("zipcode", "").strip(),
        country=fields.get("country", "").strip(),
        dob=dob
    )
    
    if TEST_RUN:
        print(f"[DRY RUN] Would create user: {user_data.model_dump()}")
        return f"dry_run_user_{email.replace('@', '_').replace('.', '_')}"
    
    try:
        # Create user in production Airtable
        users_table = Api(api_key=settings.airtable_token).table(PRODUCTION_BASE_ID, PROD_USERS_TABLE_ID)
        record = users_table.create(user_data.model_dump())
        user_id = record["id"]
        user_link = format_record_id(user_id, PRODUCTION_BASE_ID, PROD_USERS_TABLE_ID, "View User")
        print(f"   ✅ Created user {email} ({user_link})")
        
        # Print full record data for verification
        print(f"   📋 User Record Data:")
        for key, value in record["fields"].items():
            print(f"      {key}: {value}")
        print()
        
        return user_id
    except Exception as e:
        print(f"   ❌ Error creating user {email}: {e}")
        return None


def create_daydream_event(daydream_event: Dict[str, Any], owner_id: str) -> Optional[str]:
    """Create a Daydream event in Podium production."""
    fields = daydream_event.get("fields", {})
    
    event_name = fields.get("event_name", "").strip()
    if not event_name:
        print(f"No event name found for event {daydream_event.get('id', 'unknown')}")
        return None
    
    # Create event description
    location = fields.get("location", "").strip()
    
    if location:
        description = f"A high school game jam happening in {location}!"
    else:
        description = "A high school game jam!"
    
    # Generate slug from event name
    slug = slugify(event_name)
    
    # Check for existing events with same name or slug
    duplicate_check = check_event_exists(event_name, slug)
    if duplicate_check["exists"]:
        if duplicate_check["by_name"] and duplicate_check["by_slug"]:
            print(f"   ⚠️  Event already exists with both same name and slug:")
            name_link = format_record_id(duplicate_check["name_match"]["id"], PRODUCTION_BASE_ID, PROD_EVENTS_TABLE_ID, "Name Match")
            slug_link = format_record_id(duplicate_check["slug_match"]["id"], PRODUCTION_BASE_ID, PROD_EVENTS_TABLE_ID, "Slug Match")
            print(f"      Name match: {name_link}")
            print(f"      Slug match: {slug_link}")
        elif duplicate_check["by_name"]:
            name_link = format_record_id(duplicate_check["name_match"]["id"], PRODUCTION_BASE_ID, PROD_EVENTS_TABLE_ID, "Name Match")
            print(f"   ⚠️  Event already exists with same name: {name_link}")
        elif duplicate_check["by_slug"]:
            slug_link = format_record_id(duplicate_check["slug_match"]["id"], PRODUCTION_BASE_ID, PROD_EVENTS_TABLE_ID, "Slug Match")
            print(f"   ⚠️  Event already exists with same slug: {slug_link}")
        
        print(f"   ⏭️  Skipping event creation to avoid duplicates")
        return "DUPLICATE_EVENT"
    
    # Create event payload with daydream settings
    event_data = EventCreationPayload(
        name=event_name,
        description=description[:500],  # Truncate to max length
        votable=False,  # Disabled for daydream events
        leaderboard_enabled=False,  # Disabled for daydream events
        demo_links_optional=True,
    )
    
    # Create a temporary Event object to handle feature flags
    temp_event = Event(
        **event_data.model_dump(),
        id="",  # Placeholder
        owner=[owner_id],
        slug=slug,
        feature_flags_csv="daydream"  # Add daydream tag
    )
    
    
    if TEST_RUN:
        print(f"[DRY RUN] Would create event: {temp_event.model_dump(exclude={'id', 'max_votes_per_user', 'owned', 'feature_flags_list'})}")
        print(f"[DRY RUN] Owner ID: {owner_id}")
        print(f"[DRY RUN] Slug: {slug}")
        return f"dry_run_event_{slug}"
    
    try:
        # Create event in production Airtable
        events_table = Api(api_key=settings.airtable_token).table(PRODUCTION_BASE_ID, PROD_EVENTS_TABLE_ID)
        
        # Prepare event data for Airtable
        event_record = {
            **temp_event.model_dump(exclude={"id", "max_votes_per_user", "owned", "feature_flags_list"}),
            "owner": [owner_id],  # Single record field
            "slug": slug,
            "ysws_checks_enabled": True,  # Enable YSWS checks
            "join_code": generate_join_code()  # Generate a join code
        }
        
        record = events_table.create(event_record)
        event_id = record["id"]
        event_link = format_record_id(event_id, PRODUCTION_BASE_ID, PROD_EVENTS_TABLE_ID, "View Event")
        print(f"   ✅ Created event '{event_name}' ({event_link})")
        
        # Print full record data for verification
        print(f"   📋 Event Record Data:")
        for key, value in record["fields"].items():
            print(f"      {key}: {value}")
        print()
        
        return event_id
    except Exception as e:
        print(f"   ❌ Error creating event '{event_name}': {e}")
        return None


def generate_join_code() -> str:
    """Generate a random 4-character join code."""
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))


def migrate_attendees_for_event(daydream_event_id: str, podium_event_id: str, daydream_attendees: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Migrate attendees for a specific Daydream event."""
    print("   📋 Migrating attendees for event...")
    
    # Filter attendees for this specific event
    event_attendees = []
    for attendee in daydream_attendees:
        attendee_events = attendee.get("fields", {}).get("event", [])
        if isinstance(attendee_events, list) and daydream_event_id in attendee_events:
            event_attendees.append(attendee)
    
    if not event_attendees:
        print("   ℹ️  No attendees found for this event")
        return {
            "total_attendees": 0,
            "successful": 0,
            "failed": 0,
            "duplicates": 0,
            "successful_attendees": [],
            "failed_attendees": [],
            "duplicate_attendees": []
        }
    
    print(f"   Found {len(event_attendees)} attendees for this event")
    
    # Track results
    successful_attendees = []
    failed_attendees = []
    duplicate_attendees = []
    
    for attendee in event_attendees:
        attendee_id = attendee.get("id", "unknown")
        attendee_email = attendee.get("fields", {}).get("email", "").strip()
        attendee_name = attendee.get("fields", {}).get("first_name", "") + " " + attendee.get("fields", {}).get("last_name", "")
        
        # Create or find user
        user_id = create_or_find_attendee_user(attendee)
        
        if user_id == "DUPLICATE_EMAIL":
            print(f"      ⚠️  {attendee_name} ({attendee_email}) - Skipped (duplicate email)")
            duplicate_attendees.append({
                "attendee_id": attendee_id,
                "email": attendee_email,
                "name": attendee_name,
                "reason": "Multiple Podium accounts found"
            })
            continue
        elif not user_id:
            print(f"      ❌ {attendee_name} ({attendee_email}) - Failed to create/find user")
            failed_attendees.append({
                "attendee_id": attendee_id,
                "email": attendee_email,
                "name": attendee_name,
                "reason": "Failed to create/find user"
            })
            continue
        
        # Add user to event attendees (this would be done in production)
        if not TEST_RUN:
            try:
                # Update the event to add this user as an attendee
                events_table = Api(api_key=settings.airtable_token).table(PRODUCTION_BASE_ID, PROD_EVENTS_TABLE_ID)
                # Get current attendees
                event_record = events_table.get(podium_event_id)
                current_attendees = event_record["fields"].get("attendees", [])
                
                # Add new attendee if not already present
                if user_id not in current_attendees:
                    current_attendees.append(user_id)
                    events_table.update(podium_event_id, {"attendees": current_attendees})
                    print(f"      ✅ {attendee_name} - Added as attendee")
                else:
                    print(f"      ℹ️  {attendee_name} - Already an attendee")
            except Exception as e:
                print(f"      ❌ {attendee_name} - Error adding to event: {e}")
                failed_attendees.append({
                    "attendee_id": attendee_id,
                    "email": attendee_email,
                    "name": attendee_name,
                    "reason": f"Error adding to event: {e}"
                })
                continue
        else:
            print(f"      [DRY RUN] {attendee_name} - Would add as attendee")
        
        # Create links for the JSON output
        attendee_link = airtable_link(attendee_id, DAYDREAM_BASE_ID, DAYDREAM_ATTENDEES_TABLE_ID)
        user_link = airtable_link(user_id, PRODUCTION_BASE_ID, PROD_USERS_TABLE_ID)
        
        successful_attendees.append({
            "attendee_id": attendee_id,
            "user_id": user_id,
            "email": attendee_email,
            "name": attendee_name,
            "attendee_link": attendee_link,
            "user_link": user_link,
            "podium_user_record_id": user_id if not user_id.startswith("dry_run_") else None,
            "daydream_attendee_record_id": attendee_id
        })
    
    print(f"   📊 Attendees: {len(successful_attendees)} successful, {len(failed_attendees)} failed, {len(duplicate_attendees)} duplicates")
    
    return {
        "total_attendees": len(event_attendees),
        "successful": len(successful_attendees),
        "failed": len(failed_attendees),
        "duplicates": len(duplicate_attendees),
        "successful_attendees": successful_attendees,
        "failed_attendees": failed_attendees,
        "duplicate_attendees": duplicate_attendees
    }


def check_user_exists(email: str) -> Optional[str]:
    """Check if user exists and return their ID if they do."""
    return get_user_record_id_by_email_production(email)


def save_migration_progress(
    results: Dict[str, Any], 
    results_file: str
) -> None:
    """Save migration progress to JSON file."""
    try:
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        
        # Save main results (contains all detailed record data)
        results_path = os.path.join("logs", results_file)
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"   💾 Progress saved to logs/{results_file}")
    except Exception as e:
        print(f"   ⚠️  Warning: Could not save progress: {e}")


def load_migration_progress(results_file: str) -> Optional[Dict[str, Any]]:
    """Load previous migration progress from JSON file."""
    try:
        results_path = os.path.join("logs", results_file)
        if not os.path.exists(results_path):
            return None
        
        with open(results_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"   ⚠️  Warning: Could not load progress from {results_file}: {e}")
        return None


def verify_record_exists(record_id: str, base_id: str, table_id: str) -> bool:
    """Verify that a record exists in Airtable."""
    try:
        api = Api(api_key=settings.airtable_token)
        table = api.table(base_id, table_id)
        record = table.get(record_id)
        return record is not None
    except Exception as e:
        # If we get permission errors, assume the record exists (don't fail verification)
        if "403" in str(e) or "INVALID_PERMISSIONS" in str(e):
            print(f"   ⚠️  Permission error verifying record {record_id} - assuming exists")
            return True
        print(f"   ⚠️  Error verifying record {record_id}: {e}")
        return False


def verify_migration_records(progress: Dict[str, Any]) -> Dict[str, Any]:
    """Verify that all previously created records still exist."""
    print("🔍 Verifying previously created records...")
    
    verified_progress = {
        "timestamp": progress.get("timestamp"),
        "test_run": progress.get("test_run"),
        "total_processed": progress.get("total_processed", 0),
        "successful_migrations": [],
        "failed_migrations": [],
        "skipped_migrations": [],
        "duplicate_migrations": []
    }
    
    # Verify successful migrations
    for migration in progress.get("successful_migrations", []):
        daydream_event_id = migration.get("daydream_event_id")
        podium_event_id = migration.get("podium_event_id")
        owner_id = migration.get("owner_id")
        
        # Verify event exists
        event_exists = verify_record_exists(podium_event_id, PRODUCTION_BASE_ID, PROD_EVENTS_TABLE_ID)
        # Verify owner exists
        owner_exists = verify_record_exists(owner_id, PRODUCTION_BASE_ID, PROD_USERS_TABLE_ID)
        
        if event_exists and owner_exists:
            verified_progress["successful_migrations"].append(migration)
            print(f"   ✅ {migration.get('event_name', 'Unknown')} - Event and owner verified")
        else:
            # Move to failed migrations if verification fails
            verified_progress["failed_migrations"].append({
                "event_id": daydream_event_id,
                "event_name": migration.get("event_name", "Unknown"),
                "error": f"Verification failed - Event exists: {event_exists}, Owner exists: {owner_exists}"
            })
            print(f"   ❌ {migration.get('event_name', 'Unknown')} - Verification failed")
    
    # Keep other migration types as-is (they don't need verification)
    verified_progress["failed_migrations"].extend(progress.get("failed_migrations", []))
    verified_progress["skipped_migrations"].extend(progress.get("skipped_migrations", []))
    verified_progress["duplicate_migrations"].extend(progress.get("duplicate_migrations", []))
    
    # Update counts
    verified_progress["successful"] = len(verified_progress["successful_migrations"])
    verified_progress["failed"] = len(verified_progress["failed_migrations"])
    verified_progress["skipped"] = len(verified_progress["skipped_migrations"])
    verified_progress["duplicates"] = len(verified_progress["duplicate_migrations"])
    
    print(f"   📊 Verification complete: {verified_progress['successful']} verified, {verified_progress['failed']} failed verification")
    
    return verified_progress


def get_processed_event_ids(progress: Dict[str, Any]) -> set:
    """Get set of event IDs that have already been processed."""
    processed_ids = set()
    
    # Add successful migrations
    for migration in progress.get("successful_migrations", []):
        processed_ids.add(migration.get("daydream_event_id"))
    
    # Add failed migrations
    for migration in progress.get("failed_migrations", []):
        processed_ids.add(migration.get("event_id"))
    
    # Add skipped migrations
    for migration in progress.get("skipped_migrations", []):
        processed_ids.add(migration.get("event_id"))
    
    # Add duplicate migrations
    for migration in progress.get("duplicate_migrations", []):
        processed_ids.add(migration.get("event_id"))
    
    return processed_ids


def find_latest_migration_file() -> Optional[str]:
    """Find the most recent migration results file."""
    try:
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            return None
        
        # Look for migration results files
        pattern = "daydream_migration_results_production_*.json"
        import glob
        files = glob.glob(os.path.join(logs_dir, pattern))
        
        if not files:
            return None
        
        # Sort by modification time, newest first
        files.sort(key=os.path.getmtime, reverse=True)
        return os.path.basename(files[0])
    except Exception as e:
        print(f"   ⚠️  Warning: Could not find migration files: {e}")
        return None

def confirm_event_migration(event_name: str, event_id: str, owner_email: str) -> bool:
    """Ask user for confirmation before migrating a specific event."""
    print(f"\n📋 READY TO MIGRATE EVENT:")
    print(f"   Name: {event_name}")
    print(f"   Daydream Event: {format_record_id(event_id, DAYDREAM_BASE_ID, DAYDREAM_TABLE_ID)}")
    print(f"   Owner: {owner_email}")
    
    # Check if user exists
    existing_user_id = check_user_exists(owner_email)
    if existing_user_id:
        user_link = format_record_id(existing_user_id, PRODUCTION_BASE_ID, PROD_USERS_TABLE_ID, "View User")
        print(f"   User Status: ✅ EXISTING USER ({user_link})")
        print(f"   Action: Will set existing user as event owner")
    else:
        print(f"   User Status: 🆕 NEW USER")
        print(f"   Action: Will create new user and set as event owner")
    
    print(f"   Mode: {'DRY RUN (no changes)' if TEST_RUN else 'PRODUCTION (will create event)'}")
    print()
    
    while True:
        response = input("Migrate this event? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no.")


def migrate_daydream_events(resume_from_file: str = None, skip_verification: bool = False):
    """Main migration function."""
    print("=" * 80)
    print("DAYDREAM EVENTS MIGRATION")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if TEST_RUN else 'PRODUCTION'}")
    print(f"Per-event confirmation: {'ENABLED' if ENABLE_PER_EVENT_CONFIRMATION else 'DISABLED'}")
    if not TEST_RUN:
        print("🚨 WARNING: This will create REAL events in production!")
        print("   Make sure you want to proceed before continuing.")
        print()
    print(f"Daydream Base ID: {DAYDREAM_BASE_ID} (READ-ONLY)")
    print(f"Production Base ID: {PRODUCTION_BASE_ID} (WRITE TARGET)")
    print("⚠️  SAFETY: This script ONLY READS from Daydream base, NEVER writes to it")
    print()
    
    # Check for resuming
    previous_progress = None
    if resume_from_file:
        print(f"🔄 RESUMING from file: {resume_from_file}")
        previous_progress = load_migration_progress(resume_from_file)
        if previous_progress:
            print(f"   ✅ Loaded previous progress: {previous_progress.get('total_processed', 0)} events processed")
            # Verify records still exist (unless skipped)
            if not skip_verification:
                previous_progress = verify_migration_records(previous_progress)
            else:
                print("   ⏭️  Skipping record verification")
        else:
            print(f"   ❌ Could not load previous progress, starting fresh")
            resume_from_file = None
    elif not TEST_RUN:
        # Auto-detect latest migration file for resuming
        latest_file = find_latest_migration_file()
        if latest_file:
            print(f"🔍 Found previous migration file: {latest_file}")
            response = input("Resume from this file? (y/n): ").strip().lower()
            if response in ['y', 'yes']:
                resume_from_file = latest_file
                previous_progress = load_migration_progress(resume_from_file)
                if previous_progress:
                    print(f"   ✅ Resuming from: {previous_progress.get('total_processed', 0)} events processed")
                    # Verify records still exist (unless skipped)
                    if not skip_verification:
                        previous_progress = verify_migration_records(previous_progress)
                    else:
                        print("   ⏭️  Skipping record verification")
                else:
                    print(f"   ❌ Could not load previous progress, starting fresh")
                    resume_from_file = None
    
    # Pull Daydream events and attendees
    daydream_events = get_daydream_events()
    if not daydream_events:
        print("No Daydream events found. Exiting.")
        return
    
    daydream_attendees = get_daydream_attendees()
    print(f"Found {len(daydream_attendees)} total Daydream attendees")
    print()
    
    # Filter events for migration - skip events without email
    events_to_migrate = []
    skipped_count = 0
    for event in daydream_events:
        email = event.get("fields", {}).get("email", "").strip()
        if email:  # Only include events with email
            events_to_migrate.append(event)
        else:
            skipped_count += 1
    
    if TEST_RUN:
        events_to_migrate = events_to_migrate[:1]  # Only first event for test run
        print(f"[DRY RUN] Processing only first event for testing")
    
    # Filter out already processed events if resuming
    if previous_progress:
        processed_ids = get_processed_event_ids(previous_progress)
        original_count = len(events_to_migrate)
        events_to_migrate = [event for event in events_to_migrate if event.get("id") not in processed_ids]
        skipped_processed = original_count - len(events_to_migrate)
        if skipped_processed > 0:
            print(f"⏭️  Skipping {skipped_processed} already processed events")
    
    print(f"Found {len(events_to_migrate)} events with valid email addresses")
    if skipped_count > 0:
        print(f"Skipped {skipped_count} events without email addresses")
    print()
    
    # Initialize results from previous progress or start fresh
    if previous_progress and resume_from_file:
        successful_migrations = previous_progress.get("successful_migrations", [])
        failed_migrations = previous_progress.get("failed_migrations", [])
        skipped_migrations = previous_progress.get("skipped_migrations", [])
        duplicate_migrations = previous_progress.get("duplicate_migrations", [])
        results_file = resume_from_file
        print(f"📊 Previous progress: {len(successful_migrations)} successful, {len(failed_migrations)} failed, {len(skipped_migrations)} skipped, {len(duplicate_migrations)} duplicates")
    else:
        successful_migrations = []
        failed_migrations = []
        skipped_migrations = []
        duplicate_migrations = []
        
        # Set up file name for incremental saving
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f"daydream_migration_results_{'test' if TEST_RUN else 'production'}_{timestamp_str}.json"
    
    for i, event in enumerate(events_to_migrate, 1):
        event_id = event.get("id", "unknown")
        event_name = event.get("fields", {}).get("event_name", "Unknown")
        owner_email = event.get("fields", {}).get("email", "").strip()
        
        print(f"{i}. Event: {event_name} (ID: {event_id})")
        
        # Ask for confirmation for this specific event (if enabled)
        if ENABLE_PER_EVENT_CONFIRMATION:
            if not confirm_event_migration(event_name, event_id, owner_email):
                print(f"   ⏭️  Skipped by user")
                skipped_migrations.append({
                    "event_id": event_id,
                    "event_name": event_name,
                    "reason": "Skipped by user"
                })
                
                # Save progress after skipping by user
                current_results = {
                    "timestamp": datetime.now().isoformat(),
                    "test_run": TEST_RUN,
                    "total_processed": i,
                    "successful": len(successful_migrations),
                    "failed": len(failed_migrations),
                    "skipped": len(skipped_migrations),
                    "duplicates": len(duplicate_migrations),
                    "successful_migrations": successful_migrations,
                    "failed_migrations": failed_migrations,
                    "skipped_migrations": skipped_migrations,
                    "duplicate_migrations": duplicate_migrations
                }
                save_migration_progress(current_results, results_file)
                continue
        else:
            print(f"   ⚡ Auto-proceeding (confirmations disabled)")
        
        # Create or find user
        owner_id = create_or_find_user(event)
        if not owner_id:
            print(f"   ❌ Failed to create/find user")
            failed_migrations.append({
                "event_id": event_id,
                "event_name": event_name,
                "error": "Failed to create/find user"
            })
            
            # Save progress after user creation failure
            current_results = {
                "timestamp": datetime.now().isoformat(),
                "test_run": TEST_RUN,
                "total_processed": i,
                "successful": len(successful_migrations),
                "failed": len(failed_migrations),
                "skipped": len(skipped_migrations),
                "duplicates": len(duplicate_migrations),
                "successful_migrations": successful_migrations,
                "failed_migrations": failed_migrations,
                "skipped_migrations": skipped_migrations,
                "duplicate_migrations": duplicate_migrations
            }
            save_migration_progress(current_results, results_file)
            continue
        
        # Create event
        podium_event_id = create_daydream_event(event, owner_id)
        if not podium_event_id:
            print(f"   ❌ Failed to create event")
            failed_migrations.append({
                "event_id": event_id,
                "event_name": event_name,
                "error": "Failed to create event"
            })
            
            # Save progress after event creation failure
            current_results = {
                "timestamp": datetime.now().isoformat(),
                "test_run": TEST_RUN,
                "total_processed": i,
                "successful": len(successful_migrations),
                "failed": len(failed_migrations),
                "skipped": len(skipped_migrations),
                "duplicates": len(duplicate_migrations),
                "successful_migrations": successful_migrations,
                "failed_migrations": failed_migrations,
                "skipped_migrations": skipped_migrations,
                "duplicate_migrations": duplicate_migrations
            }
            save_migration_progress(current_results, results_file)
            continue
        elif podium_event_id == "DUPLICATE_EVENT":
            print(f"   ⏭️  Skipped duplicate event")
            duplicate_migrations.append({
                "event_id": event_id,
                "event_name": event_name,
                "reason": "Event already exists with same name or slug"
            })
            
            # Save progress after skipping duplicate
            current_results = {
                "timestamp": datetime.now().isoformat(),
                "test_run": TEST_RUN,
                "total_processed": i,
                "successful": len(successful_migrations),
                "failed": len(failed_migrations),
                "skipped": len(skipped_migrations),
                "duplicates": len(duplicate_migrations),
                "successful_migrations": successful_migrations,
                "failed_migrations": failed_migrations,
                "skipped_migrations": skipped_migrations,
                "duplicate_migrations": duplicate_migrations
            }
            save_migration_progress(current_results, results_file)
            continue
        
        print(f"   ✅ Successfully migrated {event_name}")
        
        # Migrate attendees for this event
        attendee_results = migrate_attendees_for_event(event_id, podium_event_id, daydream_attendees)
        
        successful_migrations.append({
            "daydream_event_id": event_id,
            "podium_event_id": podium_event_id,
            "event_name": event_name,
            "owner_id": owner_id,
            "daydream_event_link": airtable_link(event_id, DAYDREAM_BASE_ID, DAYDREAM_TABLE_ID),
            "podium_event_link": airtable_link(podium_event_id, PRODUCTION_BASE_ID, PROD_EVENTS_TABLE_ID),
            "podium_user_link": airtable_link(owner_id, PRODUCTION_BASE_ID, PROD_USERS_TABLE_ID),
            "attendee_migration": attendee_results
        })
        print()
        
        # Save progress after each event (including duplicates and failures)
        current_results = {
            "timestamp": datetime.now().isoformat(),
            "test_run": TEST_RUN,
            "total_processed": i,  # Current progress
            "successful": len(successful_migrations),
            "failed": len(failed_migrations),
            "skipped": len(skipped_migrations),
            "duplicates": len(duplicate_migrations),
            "successful_migrations": successful_migrations,
            "failed_migrations": failed_migrations,
            "skipped_migrations": skipped_migrations,
            "duplicate_migrations": duplicate_migrations
        }
        
        # Save progress incrementally
        save_migration_progress(current_results, results_file)
    
    # Calculate attendee statistics
    total_attendees = 0
    successful_attendees = 0
    failed_attendees = 0
    duplicate_attendees = 0
    
    for migration in successful_migrations:
        attendee_data = migration.get("attendee_migration", {})
        total_attendees += attendee_data.get("total_attendees", 0)
        successful_attendees += attendee_data.get("successful", 0)
        failed_attendees += attendee_data.get("failed", 0)
        duplicate_attendees += attendee_data.get("duplicates", 0)
    
    # Print summary
    print("=" * 80)
    print("MIGRATION SUMMARY")
    print("=" * 80)
    print(f"Total events processed: {len(events_to_migrate)}")
    print(f"Successful migrations: {len(successful_migrations)}")
    print(f"Failed migrations: {len(failed_migrations)}")
    print(f"Skipped by user: {len(skipped_migrations)}")
    print(f"Duplicate events (skipped): {len(duplicate_migrations)}")
    print()
    print(f"ATTENDEE STATISTICS:")
    print(f"Total attendees processed: {total_attendees}")
    print(f"Successful attendee migrations: {successful_attendees}")
    print(f"Failed attendee migrations: {failed_attendees}")
    print(f"Duplicate emails (skipped): {duplicate_attendees}")
    print()
    
    if successful_migrations:
        print("✅ SUCCESSFUL MIGRATIONS:")
        for migration in successful_migrations:
            event_link = format_record_id(migration['podium_event_id'], PRODUCTION_BASE_ID, PROD_EVENTS_TABLE_ID, "View Event")
            attendee_data = migration.get("attendee_migration", {})
            print(f"   - {migration['event_name']} ({event_link})")
            print(f"     Attendees: {attendee_data.get('successful', 0)}/{attendee_data.get('total_attendees', 0)} migrated")
            if attendee_data.get('duplicates', 0) > 0:
                print(f"     Duplicates skipped: {attendee_data.get('duplicates', 0)}")
        print()
    
    if failed_migrations:
        print("❌ FAILED MIGRATIONS:")
        for migration in failed_migrations:
            print(f"   - {migration['event_name']}: {migration['error']}")
        print()
    
    if duplicate_migrations:
        print("⚠️  DUPLICATE EVENTS (SKIPPED):")
        for migration in duplicate_migrations:
            print(f"   - {migration['event_name']}: {migration['reason']}")
        print()
    
    # Final save (results are already saved incrementally, this is just the final summary)
    print(f"Final results saved to: logs/{results_file}")


def main():
    """Main function."""
    try:
        # Check for command line arguments
        resume_file = None
        skip_verification = False
        
        i = 1
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg == "--resume" and i + 1 < len(sys.argv):
                resume_file = sys.argv[i + 1]
                i += 2
            elif arg == "--skip-verification":
                skip_verification = True
                i += 1
            elif arg == "--help":
                print("Usage: python migrate_daydream_events.py [options]")
                print("  --resume <filename>      Resume migration from a specific results file")
                print("  --skip-verification     Skip record verification when resuming")
                print("  --help                  Show this help message")
                return
            else:
                print(f"Unknown argument: {arg}")
                print("Use --help for usage information")
                return
        
        migrate_daydream_events(resume_from_file=resume_file, skip_verification=skip_verification)
    except KeyboardInterrupt:
        print("\nMigration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Migration failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
