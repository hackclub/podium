"""
Test endpoints for stress testing.

Security:
- Only available when env != "production" AND enable_test_endpoints = true
- Both checks normalized and enforced in ensure_test_enabled() dependency

Endpoints:
- POST /test/token - Generate JWT tokens without email verification
- POST /test/bootstrap - Create ephemeral test events and seed data
- POST /test/cleanup - Delete all test data by run_id

Design:
- All test data tagged with run_id for deterministic cleanup
- Uses name-based formulas (not ID-based) because Airtable linked fields expose primary field text
- Cleans up in dependency order: votes → projects → events → referrals → users
"""

import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from podium import db, settings, cache
from pyairtable.formulas import FIND
from podium.db.user import UserInternal
from datetime import timedelta


def ensure_test_enabled():
    """Guard to ensure test endpoints are only available in non-production with feature flag."""
    env = str(settings.get("env", "development")).lower()
    if env in ("production", "prod"):
        raise HTTPException(
            status_code=403,
            detail="Test endpoints disabled in production environment"
        )
    if not settings.get("enable_test_endpoints", False):
        raise HTTPException(
            status_code=403,
            detail="Test endpoints not enabled. Set PODIUM_ENABLE_TEST_ENDPOINTS=true to enable."
        )


router = APIRouter(
    prefix="/test",
    tags=["test"],
    dependencies=[Depends(ensure_test_enabled)]
)


@router.post("/token")
async def test_token(email: str):
    """
    Generate access token without email verification for load testing.
    
    Bypasses magic link flow - creates or retrieves user and immediately returns JWT.
    Users created here are tagged with "LoadTest" last_name for cleanup tracking.
    """
    from podium.routers.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
    
    # Try to get existing user (avoid duplicate creation)
    user = None
    try:
        user = cache.get_user_by_email(email, UserInternal)
    except (KeyError, AttributeError):
        pass
    
    # Create minimal test user if doesn't exist
    if user is None:
        display_name = email.split("@")[0]
        user_data = {
            "email": email,
            "display_name": display_name,
            "first_name": display_name,
            "last_name": "LoadTest",  # Tag for cleanup
        }
        record = db.tables["users"].create(user_data)
        user = UserInternal.model_validate({"id": record["id"], **record["fields"]})
    
    # Generate standard access token
    token = create_access_token(
        {"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )
    return {"access_token": token, "token_type": "bearer"}


class BootstrapRequest(BaseModel):
    run_id: Optional[str] = None
    events: int = 5
    seed_projects_per_event: int = 3


class BootstrapResponse(BaseModel):
    run_id: str
    events: list[dict]


class CleanupRequest(BaseModel):
    run_id: str


class CleanupResponse(BaseModel):
    run_id: str
    deleted_events: int
    deleted_projects: int
    deleted_votes: int
    deleted_referrals: int
    deleted_users: int
    errors: list[str] = []


@router.post("/bootstrap", response_model=BootstrapResponse)
async def bootstrap_test_data(req: BootstrapRequest):
    """
    Create ephemeral test data for stress testing.
    
    Creates:
    - N events with deterministic slugs (lt-{run_id}-{i})
    - Seed projects for each event (owned by seed bot user)
    - Seed bot user to own the projects and attend events
    
    Tagging strategy:
    - Event slugs: lt-{run_id}-{i} for discoverable cleanup
    - Project names: include run_id for name-based formula cleanup
    - User emails: seed_{run_id}@loadtest.com and user_{run_id}_*@loadtest.com
    
    Returns event IDs and join_codes for stress test to use.
    """
    # Generate run_id from epoch if not provided (unique per test run)
    run_id = req.run_id or str(int(time.time()))
    
    # Create seed bot user to own all test events and seed projects
    seed_email = f"seed_{run_id}@loadtest.com"
    seed_user_data = {
        "email": seed_email,
        "display_name": f"Seed Bot {run_id}",
        "first_name": "Seed",
        "last_name": "LoadTest",
    }
    seed_user_record = db.tables["users"].create(seed_user_data)
    seed_user_id = seed_user_record["id"]
    
    events_created = []
    
    # Create test events with predictable slugs and join codes
    for i in range(req.events):
        event_slug = f"lt-{run_id}-{i}"  # Discoverable via FIND formula in cleanup
        event_data = {
            "name": f"LoadTest {run_id} #{i}",
            "slug": event_slug,
            "description": f"Ephemeral load test event (run {run_id})",
            "owner": [seed_user_id],
            "attendees": [seed_user_id],  # Seed bot also attends (needed for project creation)
            "join_code": f"LT{run_id}{i}",
            "votable": True,
            "leaderboard_enabled": True,
        }
        
        event_record = db.tables["events"].create(event_data)
        event_id = event_record["id"]
        
        # Create seed projects (gives users something to browse/vote on immediately)
        for j in range(req.seed_projects_per_event):
            project_data = {
                "name": f"Test Project {run_id}-{i}-{j}",  # run_id in name for cleanup formula
                "description": "Seed project for load testing",
                "event": [event_id],
                "owner": [seed_user_id],
            }
            db.tables["projects"].create(project_data)
        
        events_created.append({
            "id": event_id,
            "slug": event_slug,
            "name": event_data["name"],
            "join_code": event_data["join_code"],
        })
    
    return BootstrapResponse(
        run_id=run_id,
        events=events_created
    )


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_test_data(req: CleanupRequest):
    """
    Clean up all test data for a given run_id.
    
    Strategy:
    - Uses name-based formulas because Airtable linked fields expose primary field text, not record IDs
    - Deletes in dependency order: votes → projects → events → referrals → users
    - Invalidates cache keys for deleted entities
    - Returns counts and errors for observability
    
    Handles two cases:
    1. Events found: Delete via event relationships
    2. No events (already deleted): Delete orphaned projects/votes by run_id in names
    """
    run_id = req.run_id
    
    # Find all events for this run via slug prefix
    slug_prefix = f"lt-{run_id}-"
    events_formula = FIND(slug_prefix, "{slug}")  # FIND searches text fields
    events = db.tables["events"].all(formula=events_formula)
    
    deleted_votes = 0
    deleted_projects = 0
    deleted_events = 0
    deleted_users = 0
    deleted_referrals = 0
    errors = []
    
    # Case 1: No events found (may have been deleted already)
    # Still need to clean up orphaned projects, votes, and users
    if not events:
        # Delete test users by email pattern
        user_email_patterns = [
            f"seed_{run_id}@loadtest.com",
            f"user_{run_id}_",
        ]
        
        for pattern in user_email_patterns:
            users_formula = FIND(pattern, "{email}")
            users = db.tables["users"].all(formula=users_formula)
            
            for user in users:
                db.tables["users"].delete(user["id"])
                deleted_users += 1
                
                # Invalidate user cache
                try:
                    if "email" in user["fields"]:
                        cache.ops.delete_by_index(cache.UserSpec, "email", user["fields"]["email"])
                except:
                    pass
        
        # Delete orphaned projects by run_id in name
        try:
            projects_formula = FIND(run_id, "{name}")
            projects = db.tables["projects"].all(formula=projects_formula)
            
            for p in projects:
                # Delete votes for this project (linked field shows project name)
                project_name = p["fields"].get("name", "")
                if project_name:
                    try:
                        votes_formula = FIND(project_name, "{project}")
                        votes = db.tables["votes"].all(formula=votes_formula)
                        for v in votes:
                            db.tables["votes"].delete(v["id"])
                            deleted_votes += 1
                    except Exception as e:
                        errors.append(f"Failed to delete votes for project {project_name}: {e}")
                
                # Delete the project
                db.tables["projects"].delete(p["id"])
                deleted_projects += 1
                
                try:
                    cache.delete(cache.ProjectSpec, p["id"])
                except:
                    pass
        except Exception as e:
            errors.append(f"Failed to delete projects: {e}")
        
        return CleanupResponse(
            run_id=run_id,
            deleted_events=0,
            deleted_projects=deleted_projects,
            deleted_votes=deleted_votes,
            deleted_referrals=0,
            deleted_users=deleted_users,
            errors=errors,
        )
    
    event_ids = [e["id"] for e in events]
    
    # Case 2: Events found - delete all related data
    # Delete all projects from this test run (by run_id in project name)
    try:
        projects_formula = FIND(run_id, "{name}")
        projects = db.tables["projects"].all(formula=projects_formula)
        
        for p in projects:
            project_name = p["fields"].get("name", "")
            
            # Delete votes (Airtable vote.project linked field exposes project name, not ID)
            if project_name:
                try:
                    votes_formula = FIND(project_name, "{project}")  # Searches project name text
                    votes = db.tables["votes"].all(formula=votes_formula)
                    for v in votes:
                        db.tables["votes"].delete(v["id"])
                        deleted_votes += 1
                except Exception as e:
                    errors.append(f"Failed to delete votes for project {project_name}: {e}")
            
            # Delete the project
            db.tables["projects"].delete(p["id"])
            deleted_projects += 1
            
            try:
                cache.delete(cache.ProjectSpec, p["id"])
            except:
                pass
    except Exception as e:
        errors.append(f"Failed to delete projects: {e}")
    
    # Delete events and their referrals
    for e in events:
        event_id = e["id"]
        event_name = e["fields"].get("name", "")
        
        # Delete referrals (created when users attend events)
        if event_name:
            try:
                referrals_formula = FIND(event_name, "{event}")  # Linked field exposes event name
                referrals = db.tables["referrals"].all(formula=referrals_formula)
                for r in referrals:
                    db.tables["referrals"].delete(r["id"])
                    deleted_referrals += 1
            except Exception as ex:
                errors.append(f"Failed to delete referrals for event {event_name}: {ex}")
        
        # Delete the event
        db.tables["events"].delete(event_id)
        deleted_events += 1
        
        try:
            cache.delete(cache.EventSpec, event_id)
        except:
            pass
    
    # Delete test users (both seed bot and load test users)
    user_email_patterns = [
        f"seed_{run_id}@loadtest.com",
        f"user_{run_id}_",  # Prefix for all load test users
    ]
    
    for pattern in user_email_patterns:
        users_formula = FIND(pattern, "{email}")
        users = db.tables["users"].all(formula=users_formula)
        
        for user in users:
            db.tables["users"].delete(user["id"])
            deleted_users += 1
            
            # Invalidate user cache
            try:
                if "email" in user["fields"]:
                    cache.ops.delete_by_index(cache.UserSpec, "email", user["fields"]["email"])
            except:
                pass
    
    return CleanupResponse(
        run_id=run_id,
        deleted_events=deleted_events,
        deleted_projects=deleted_projects,
        deleted_votes=deleted_votes,
        deleted_referrals=deleted_referrals,
        deleted_users=deleted_users,
        errors=errors,
    )
