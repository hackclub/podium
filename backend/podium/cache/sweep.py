"""
Daily cache sweep to detect and remove deleted records.

Run this as a cron job once per day to clean up orphaned cache entries
when records are deleted directly in Airtable (bypassing the cache delete functions).

Usage:
    python -m podium.cache.sweep
    
Or as a cron job:
    0 2 * * * cd /path/to/backend && uv run python -m podium.cache.sweep
"""

import logging
from typing import List
from podium.db import tables
from podium.cache.models import ProjectCache, EventCache, UserCache, VoteCache, ReferralCache
from podium.cache.operations import _set_tombstone
from podium.cache.client import get_redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_all_cached_ids(model_class) -> List[str]:
    """Get all primary keys from a cache model."""
    try:
        # Get all keys for this model using redis-om's key pattern
        client = get_redis_client()
        pattern = f"{model_class.Meta.model_key_prefix}:*"
        keys = client.keys(pattern)
        
        # Extract record IDs from keys (format: prefix:record_id)
        prefix_len = len(model_class.Meta.model_key_prefix) + 1
        return [key.decode() if isinstance(key, bytes) else key[prefix_len:] for key in keys]
    except Exception as e:
        logger.error(f"Failed to get cached IDs for {model_class.__name__}: {e}")
        return []


def get_all_cached_objects(model_class) -> List[dict]:
    """Get all cached objects from a model (as dicts)."""
    try:
        cached_ids = get_all_cached_ids(model_class)
        objects = []
        for record_id in cached_ids:
            try:
                obj = model_class.get(record_id)
                if obj:
                    objects.append(obj.dict())
            except Exception:
                pass
        return objects
    except Exception as e:
        logger.error(f"Failed to get cached objects for {model_class.__name__}: {e}")
        return []


def build_referenced_ids() -> dict:
    """
    Build sets of all referenced IDs by scanning cached relationships.
    
    Returns dict with keys: events, projects, users, votes
    Each value is a set of IDs that are referenced by other cached objects.
    """
    logger.info("Building reference map from cached data...")
    
    referenced = {
        "events": set(),
        "projects": set(),
        "users": set(),
    }
    
    # Scan users for event/project references
    logger.info("  Scanning cached users...")
    users = get_all_cached_objects(UserCache)
    for user in users:
        # Events referenced by users
        if "attending_events" in user and user["attending_events"]:
            referenced["events"].update(user["attending_events"])
        if "owned_events" in user and user["owned_events"]:
            referenced["events"].update(user["owned_events"])
        
        # Projects referenced by users
        if "projects" in user and user["projects"]:
            referenced["projects"].update(user["projects"])
        if "collaborations" in user and user["collaborations"]:
            referenced["projects"].update(user["collaborations"])
    
    # Scan projects for event/user references
    logger.info("  Scanning cached projects...")
    projects = get_all_cached_objects(ProjectCache)
    for project in projects:
        # Events referenced by projects
        if "event" in project and project["event"]:
            # event is a list with single ID
            if isinstance(project["event"], list) and project["event"]:
                referenced["events"].add(project["event"][0])
        
        # Users referenced by projects
        if "owner" in project and project["owner"]:
            if isinstance(project["owner"], list) and project["owner"]:
                referenced["users"].add(project["owner"][0])
        if "collaborators" in project and project["collaborators"]:
            referenced["users"].update(project["collaborators"])
    
    # Scan votes for event/project/user references
    logger.info("  Scanning cached votes...")
    votes = get_all_cached_objects(VoteCache)
    for vote in votes:
        # Events referenced by votes
        if "event" in vote and vote["event"]:
            if isinstance(vote["event"], list) and vote["event"]:
                referenced["events"].add(vote["event"][0])
        
        # Projects referenced by votes
        if "project" in vote and vote["project"]:
            if isinstance(vote["project"], list) and vote["project"]:
                referenced["projects"].add(vote["project"][0])
        
        # Users referenced by votes
        if "voter" in vote and vote["voter"]:
            if isinstance(vote["voter"], list) and vote["voter"]:
                referenced["users"].add(vote["voter"][0])
    
    # Scan events for user references
    logger.info("  Scanning cached events...")
    events = get_all_cached_objects(EventCache)
    for event in events:
        # Users referenced by events
        if "owner" in event and event["owner"]:
            if isinstance(event["owner"], list) and event["owner"]:
                referenced["users"].add(event["owner"][0])
        if "attendees" in event and event["attendees"]:
            referenced["users"].update(event["attendees"])
    
    logger.info(f"  Referenced: {len(referenced['events'])} events, "
                f"{len(referenced['projects'])} projects, "
                f"{len(referenced['users'])} users")
    
    return referenced


def sweep_table(
    cache_model,
    table_name: str,
    model_name: str,
    referenced_ids: set = None
):
    """
    Sweep a single table to detect deletions.
    
    Uses reference checking to minimize Airtable API calls:
    1. Find cached IDs that aren't referenced by other objects (orphan candidates)
    2. Only check Airtable for suspected orphans
    3. Remove confirmed deletions and set tombstones
    """
    logger.info(f"Sweeping {model_name}...")
    
    cached_ids = get_all_cached_ids(cache_model)
    if not cached_ids:
        logger.info(f"  No cached {model_name} found")
        return
    
    logger.info(f"  Found {len(cached_ids)} cached {model_name}")
    
    # Determine which IDs to check based on references
    if referenced_ids is not None:
        cached_set = set(cached_ids)
        orphan_candidates = cached_set - referenced_ids
        
        logger.info(f"  Referenced by other objects: {len(referenced_ids & cached_set)}")
        logger.info(f"  Orphan candidates (not referenced): {len(orphan_candidates)}")
        
        # Only check orphans with Airtable
        ids_to_check = list(orphan_candidates)
    else:
        # No reference tracking, check all
        ids_to_check = cached_ids
        logger.info(f"  Checking all {len(ids_to_check)} records (no reference tracking)")
    
    if not ids_to_check:
        logger.info(f"  All {model_name} are referenced, nothing to check")
        return
    
    removed_count = 0
    error_count = 0
    
    logger.info(f"  Verifying {len(ids_to_check)} suspected orphans with Airtable...")
    
    for record_id in ids_to_check:
        try:
            # Check if record still exists in Airtable
            tables[table_name].get(record_id)
            # Record exists but not referenced - unusual but valid (keep it)
            logger.debug(f"  {record_id} exists in Airtable (orphaned but valid)")
        except Exception as e:
            # Record not found (404) or other error
            error_str = str(e).lower()
            if "404" in error_str or "not found" in error_str:
                logger.info(f"  Removing deleted {model_name}: {record_id}")
                try:
                    # Remove from cache
                    cache_model.delete(record_id)
                    # Set tombstone
                    _set_tombstone(table_name, record_id)
                    removed_count += 1
                except Exception as del_err:
                    logger.error(f"  Failed to remove {record_id}: {del_err}")
                    error_count += 1
            else:
                # Some other error (rate limit, network, etc.)
                logger.warning(f"  Error checking {record_id}: {e}")
                error_count += 1
    
    logger.info(f"  {model_name} sweep complete: {removed_count} removed, {error_count} errors, "
                f"{len(ids_to_check) - removed_count - error_count} verified")


def run_sweep():
    """
    Run the full cache sweep across all tables.
    
    Uses reference checking to minimize Airtable API calls:
    - Scans all cached objects to find referenced IDs
    - Only checks Airtable for orphan candidates (not referenced anywhere)
    - This reduces API calls by 90%+ compared to checking every cached record
    """
    logger.info("=" * 60)
    logger.info("Starting daily cache sweep (reference-optimized)")
    logger.info("=" * 60)
    
    # Check Redis connection
    try:
        client = get_redis_client()
        client.ping()
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        logger.error("Aborting sweep")
        return
    
    # Build reference map from cached data (Redis-only, very fast)
    referenced = build_referenced_ids()
    
    logger.info("")
    logger.info("Sweeping tables (checking only unreferenced records)...")
    logger.info("")
    
    # Sweep each table with reference filtering
    # Only check Airtable for IDs that aren't referenced by other cached objects
    sweep_table(EventCache, "events", "Events", referenced_ids=referenced["events"])
    sweep_table(ProjectCache, "projects", "Projects", referenced_ids=referenced["projects"])
    sweep_table(UserCache, "users", "Users", referenced_ids=referenced["users"])
    
    # Votes and referrals are not referenced by other objects, so check all
    # (But they're typically small tables, so acceptable)
    sweep_table(VoteCache, "votes", "Votes", referenced_ids=None)
    sweep_table(ReferralCache, "referrals", "Referrals", referenced_ids=None)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("Cache sweep complete")
    logger.info("=" * 60)


def main():
    """Entry point for CLI/scheduled task."""
    run_sweep()


if __name__ == "__main__":
    main()
