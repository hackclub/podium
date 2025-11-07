"""Cleanup script to delete all stress test-created objects from Airtable."""

import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

# Add backend directory to path
backend_dir = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, backend_dir)

from podium.db import tables
from pyairtable.formulas import match

# Stress test email domain from config
STRESS_TEST_EMAIL_DOMAIN = "stress-test.example.com"

# Maximum number of parallel deletions
MAX_WORKERS = 20


def delete_record(table_name: str, record_id: str) -> Tuple[str, bool, str]:
    """Delete a single record and return (table_name, success, error_message)."""
    try:
        tables[table_name].delete(record_id)
        return (table_name, True, "")
    except Exception as e:
        return (table_name, False, str(e))


def delete_records_parallel(table_name: str, records: List[dict], entity_name: str) -> int:
    """Delete records in parallel and return count of successful deletions."""
    if not records:
        return 0
    
    print(f"   Deleting {len(records)} {entity_name} in parallel...")
    deleted_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all deletion tasks
        future_to_record = {
            executor.submit(delete_record, table_name, record["id"]): record
            for record in records
        }
        
        # Process completed deletions
        for future in as_completed(future_to_record):
            record = future_to_record[future]
            try:
                table_name_result, success, error = future.result()
                if success:
                    deleted_count += 1
                else:
                    print(f"   Warning: Failed to delete {entity_name} {record.get('id', 'unknown')}: {error}")
            except Exception as e:
                print(f"   Warning: Exception deleting {entity_name} {record.get('id', 'unknown')}: {e}")
    
    return deleted_count


def cleanup_stress_test_data():
    """Delete all stress test users, events, projects, votes, and referrals."""
    print("Cleaning up stress test data...")
    print("=" * 50)
    
    deleted_counts = {
        "users": 0,
        "events": 0,
        "projects": 0,
        "votes": 0,
        "referrals": 0,
    }
    
    # 1. Find and delete stress test users
    print("\n1. Finding stress test users...")
    try:
        # Use SEARCH() formula for pattern matching (match() doesn't support wildcards)
        # Airtable formula: SEARCH returns position or error, so we check if it's not an error
        email_formula = f'NOT(ISERROR(SEARCH("@{STRESS_TEST_EMAIL_DOMAIN}", {{email}})))'
        user_records = tables["users"].all(formula=email_formula)
        print(f"   Found {len(user_records)} stress test users")
        
        deleted_counts["users"] = delete_records_parallel("users", user_records, "users")
        print(f"   Deleted {deleted_counts['users']} users")
    except Exception as e:
        print(f"   Error finding/deleting users: {e}")
        import traceback
        traceback.print_exc()
    
    # 2. Find and delete stress test events (by name pattern)
    print("\n2. Finding stress test events...")
    try:
        # Use SEARCH() formula for pattern matching
        event_formula = 'NOT(ISERROR(SEARCH("Stress Test Event", {name})))'
        event_records = tables["events"].all(formula=event_formula)
        print(f"   Found {len(event_records)} stress test events")
        
        deleted_counts["events"] = delete_records_parallel("events", event_records, "events")
        print(f"   Deleted {deleted_counts['events']} events")
    except Exception as e:
        print(f"   Error finding/deleting events: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Find and delete stress test projects (by repo URL pattern)
    print("\n3. Finding stress test projects...")
    try:
        # Use SEARCH() formula for pattern matching
        project_formula = 'NOT(ISERROR(SEARCH("stress-test", {repo})))'
        project_records = tables["projects"].all(formula=project_formula)
        print(f"   Found {len(project_records)} stress test projects")
        
        deleted_counts["projects"] = delete_records_parallel("projects", project_records, "projects")
        print(f"   Deleted {deleted_counts['projects']} projects")
    except Exception as e:
        print(f"   Error finding/deleting projects: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Find and delete stress test votes (by referral content)
    print("\n4. Finding stress test votes...")
    try:
        # Votes don't have a direct stress test identifier, but we can find them via events
        # For now, we'll skip votes as they're harder to identify uniquely
        # They'll be orphaned but harmless
        print("   Skipping votes (hard to identify uniquely, will be cleaned by sweep)")
    except Exception as e:
        print(f"   Error finding/deleting votes: {e}")
    
    # 5. Find and delete stress test referrals (by content)
    print("\n5. Finding stress test referrals...")
    try:
        # Use exact match for referrals (they use "stress_test" exactly)
        referral_records = tables["referrals"].all(formula=match({"content": "stress_test"}))
        print(f"   Found {len(referral_records)} stress test referrals")
        
        deleted_counts["referrals"] = delete_records_parallel("referrals", referral_records, "referrals")
        print(f"   Deleted {deleted_counts['referrals']} referrals")
    except Exception as e:
        print(f"   Error finding/deleting referrals: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 50)
    print("CLEANUP SUMMARY")
    print("=" * 50)
    print(f"Users deleted:    {deleted_counts['users']}")
    print(f"Events deleted:   {deleted_counts['events']}")
    print(f"Projects deleted: {deleted_counts['projects']}")
    print(f"Referrals deleted: {deleted_counts['referrals']}")
    print(f"Votes:            (skipped - will be cleaned by sweep)")
    print("\nCleanup complete!")


if __name__ == "__main__":
    try:
        cleanup_stress_test_data()
    except KeyboardInterrupt:
        print("\n\nCleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nCleanup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

