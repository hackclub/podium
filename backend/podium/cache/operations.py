"""
Cache operations with fallback to Airtable.

Implements cache-aside pattern:
1. Try to get from cache
2. On miss, fetch from Airtable
3. Store in cache for next time
4. Return validated Pydantic model
"""

from typing import List, Optional, Type, TypeVar
import random
from contextvars import ContextVar
from podium.db import tables
from podium.db.project import Project
from podium.db.event import Event, PrivateEvent
from podium.db.user import UserPrivate, UserPublic
from podium.db.vote import Vote
from podium.db.referral import Referral
from pyairtable.formulas import match
from podium.cache.models import (
    ProjectCache,
    EventCache,  # Now stores PrivateEvent
    UserCache,   # Now stores UserPrivate
    VoteCache,
    ReferralCache,
)
from podium.cache.client import get_redis_client

T = TypeVar("T")

# Context variable to track cache hits/misses per request
_cache_status: ContextVar[str] = ContextVar("cache_status", default="BYPASS")

# Cache TTL: 8 hours with ±5% jitter to prevent synchronized expiration
# Configurable: adjust based on how often you manually edit Airtable vs cache hit rate
CACHE_TTL_SECONDS = 8 * 60 * 60  # 8 hours = 28800 seconds

# Tombstone TTL: 6 hours - caches "not found" to prevent repeated 404s
TOMBSTONE_TTL_SECONDS = 6 * 60 * 60  # 6 hours = 21600 seconds


def _get_ttl() -> int:
    """Get TTL with random jitter to prevent thundering herd on expiry."""
    return int(CACHE_TTL_SECONDS * random.uniform(0.95, 1.05))


def _set_tombstone(table: str, record_id: str):
    """
    Set a tombstone marker for a deleted record.
    
    Prevents repeated 404s by caching the fact that a record doesn't exist.
    """
    try:
        client = get_redis_client()
        tombstone_key = f"tomb:{table}:{record_id}"
        client.setex(tombstone_key, TOMBSTONE_TTL_SECONDS, "1")
    except Exception:
        pass


def _check_tombstone(table: str, record_id: str) -> bool:
    """Check if a tombstone exists for this record."""
    try:
        client = get_redis_client()
        tombstone_key = f"tomb:{table}:{record_id}"
        return client.exists(tombstone_key) > 0
    except Exception:
        return False


def _get_from_cache_or_airtable(
    cache_model: Type,
    pydantic_model: Type[T],
    table_name: str,
    record_id: str,
) -> Optional[T]:
    """
    Generic helper: try cache first, fallback to Airtable.
    
    Args:
        cache_model: The redis-om JsonModel class
        pydantic_model: The Pydantic model to validate with
        table_name: Name of Airtable table
        record_id: Airtable record ID
        
    Returns:
        Validated Pydantic model instance or None if not found
    """
    # Check tombstone first (record known to not exist)
    if _check_tombstone(table_name, record_id):
        _cache_status.set("HIT")
        return None
    
    # Try cache first
    try:
        cached = cache_model.get(record_id)
        if cached:
            _cache_status.set("HIT")
            # Revalidate with original Pydantic model
            return pydantic_model(**cached.dict())
    except Exception:
        # Cache miss or error, continue to Airtable
        pass
    
    _cache_status.set("MISS")
    
    # Fetch from Airtable
    try:
        table = tables[table_name]
        record = table.get(record_id)
        
        # Always inject id from record["id"] to ensure it's present
        fields = {**record["fields"], "id": record["id"]}
        validated = pydantic_model.model_validate(fields)
        
        # Store in cache for next time with TTL (fire and forget)
        try:
            cache_model(pk=record["id"], **validated.dict()).save(ttl=_get_ttl())
        except Exception:
            # Cache write failed, but we have the data
            pass
        
        return validated
    except Exception as e:
        # Not found in Airtable - set tombstone to prevent repeated 404s
        if "404" in str(e) or "not found" in str(e).lower():
            _set_tombstone(table_name, record_id)
        return None


# ===== PROJECT OPERATIONS =====

def get_project(project_id: str) -> Optional[Project]:
    """Get project by ID from cache or Airtable."""
    return _get_from_cache_or_airtable(
        ProjectCache, Project, "projects", project_id
    )


def get_projects_for_event(event_id: str, sort_by_points: bool = False) -> List[Project]:
    """
    Get all projects for an event.
    
    This uses the cache index to query directly without hitting Airtable.
    If cache is empty, falls back to fetching from Airtable.
    """
    try:
        # Query cache using index
        query = ProjectCache.find(ProjectCache.event == event_id)
        if sort_by_points:
            query = query.sort_by("-points")
        
        cached_projects = query.all()
        
        if cached_projects:
            # Revalidate with Pydantic
            return [Project(**p.dict()) for p in cached_projects]
    except Exception:
        pass
    
    # Cache miss - fetch from Airtable and populate cache
    try:
        table = tables["projects"]
        # Query by event using Airtable formula (assumes event field contains single record ID)
        formula = match({"event": event_id})
        records = table.all(formula=formula)
        
        projects = []
        for record in records:
            # Inject id from record["id"]
            fields = {**record["fields"], "id": record["id"]}
            project = Project.model_validate(fields)
            projects.append(project)
            
            # Populate cache with TTL (fire and forget)
            try:
                ProjectCache(pk=record["id"], **project.dict()).save(ttl=_get_ttl())
            except Exception:
                pass
        
        # Sort in Python if needed (cache wasn't available for sorted query)
        if sort_by_points:
            projects.sort(key=lambda p: p.points, reverse=True)
        
        return projects
    except Exception:
        # Airtable query failed
        return []


def invalidate_project(project_id: str):
    """Remove project from cache (called by webhook)."""
    try:
        ProjectCache.delete(project_id)
    except Exception:
        pass  # Already gone or doesn't exist


def upsert_project(project: Project):
    """Update or insert project in cache (called by webhook)."""
    try:
        ProjectCache(pk=project.id, **project.dict()).save(ttl=_get_ttl())
    except Exception:
        pass  # Cache write failed


# ===== EVENT OPERATIONS =====

def get_event(event_id: str, private: bool = False) -> Optional[Event | PrivateEvent]:
    """
    Get event by ID from cache or Airtable.
    
    Always caches PrivateEvent, derives public Event on read if needed.
    """
    # Always fetch PrivateEvent from cache
    private_event = _get_from_cache_or_airtable(
        EventCache, PrivateEvent, "events", event_id
    )
    
    if not private_event:
        return None
    
    if private:
        return private_event
    
    # Derive public Event by stripping private fields
    return Event(**private_event.dict())


def get_event_by_slug(slug: str, private: bool = False) -> Optional[Event | PrivateEvent]:
    """
    Get event by slug using cache index.
    Falls back to Airtable if not in cache.
    Always caches PrivateEvent, derives Event if needed.
    """
    try:
        # Query cache using slug index (always PrivateEvent)
        result = EventCache.find(EventCache.slug == slug).first()
        if result:
            private_event = PrivateEvent(**result.dict())
            if private:
                return private_event
            return Event(**private_event.dict())
    except Exception:
        pass
    
    # Cache miss - fetch from Airtable by slug
    try:
        table = tables["events"]
        formula = match({"slug": slug})
        records = table.all(formula=formula)
        
        if records:
            # Always validate as PrivateEvent and inject id
            fields = {**records[0]["fields"], "id": records[0]["id"]}
            private_event = PrivateEvent.model_validate(fields)
            
            # Store in cache with TTL
            try:
                EventCache(pk=private_event.id, **private_event.dict()).save(ttl=_get_ttl())
            except Exception:
                pass
            
            if private:
                return private_event
            return Event(**private_event.dict())
    except Exception:
        pass
    
    return None


def invalidate_event(event_id: str):
    """Remove event from cache (called by webhook or delete)."""
    try:
        EventCache.delete(event_id)
    except Exception:
        pass


def upsert_event(event: Event | PrivateEvent):
    """
    Update or insert event in cache (called by webhook).
    
    Always stores as PrivateEvent (upgrades Event to PrivateEvent if needed).
    """
    try:
        # Ensure we're storing the full PrivateEvent
        if isinstance(event, PrivateEvent):
            private_event = event
        else:
            # Upgrade Event to PrivateEvent by adding empty private fields
            private_event = PrivateEvent(**event.dict())
        
        EventCache(pk=private_event.id, **private_event.dict()).save(ttl=_get_ttl())
    except Exception:
        pass


# ===== USER OPERATIONS =====

def get_user(user_id: str, private: bool = True) -> Optional[UserPrivate | UserPublic]:
    """
    Get user by ID from cache or Airtable.
    
    Always caches UserPrivate, derives UserPublic on read if needed.
    """
    # Always fetch UserPrivate from cache
    private_user = _get_from_cache_or_airtable(
        UserCache, UserPrivate, "users", user_id
    )
    
    if not private_user:
        return None
    
    if private:
        return private_user
    
    # Derive public UserPublic by stripping private fields
    return UserPublic(**private_user.dict())


def get_user_by_email(email: str) -> Optional[UserPrivate]:
    """
    Get user by email using cache index.
    Falls back to Airtable if not in cache.
    """
    # Normalize email for consistent cache lookups
    normalized_email = email.lower().strip()
    
    try:
        # Query cache using email index
        result = UserCache.find(UserCache.email == normalized_email).first()
        if result:
            return UserPrivate(**result.dict())
    except Exception:
        pass
    
    # Cache miss - fetch from Airtable
    try:
        table = tables["users"]
        formula = match({"email": normalized_email})
        records = table.all(formula=formula)
        
        if records:
            # Inject id from record["id"]
            fields = {**records[0]["fields"], "id": records[0]["id"]}
            validated = UserPrivate.model_validate(fields)
            
            # Store in cache with TTL
            try:
                UserCache(pk=records[0]["id"], **validated.dict()).save(ttl=_get_ttl())
            except Exception:
                pass
            return validated
    except Exception:
        pass
    
    return None


def invalidate_user(user_id: str):
    """Remove user from cache (called by webhook or delete)."""
    try:
        UserCache.delete(user_id)
    except Exception:
        pass


def upsert_user(user: UserPrivate):
    """
    Update or insert user in cache (called by webhook).
    
    Always stores UserPrivate.
    """
    try:
        # Normalize email to lowercase for consistent cache lookups
        user_data = user.dict()
        if "email" in user_data and user_data["email"]:
            user_data["email"] = user_data["email"].lower().strip()
        
        UserCache(pk=user.id, **user_data).save(ttl=_get_ttl())
    except Exception:
        pass


# ===== VOTE OPERATIONS =====

def get_vote(vote_id: str) -> Optional[Vote]:
    """Get vote by ID from cache or Airtable."""
    return _get_from_cache_or_airtable(
        VoteCache, Vote, "votes", vote_id
    )


def get_votes_for_event(event_id: str) -> List[Vote]:
    """Get all votes for an event using cache index."""
    try:
        cached_votes = VoteCache.find(VoteCache.event == event_id).all()
        if cached_votes:
            return [Vote(**v.dict()) for v in cached_votes]
    except Exception:
        pass
    
    # Cache miss - fetch from Airtable
    try:
        table = tables["votes"]
        formula = match({"event": event_id})
        records = table.all(formula=formula)
        
        votes = []
        for record in records:
            # Inject id from record["id"]
            fields = {**record["fields"], "id": record["id"]}
            vote = Vote.model_validate(fields)
            votes.append(vote)
            
            # Populate cache with TTL
            try:
                VoteCache(pk=record["id"], **vote.dict()).save(ttl=_get_ttl())
            except Exception:
                pass
        
        return votes
    except Exception:
        return []


def get_votes_for_project(project_id: str) -> List[Vote]:
    """Get all votes for a project using cache index."""
    try:
        cached_votes = VoteCache.find(VoteCache.project == project_id).all()
        if cached_votes:
            return [Vote(**v.dict()) for v in cached_votes]
    except Exception:
        pass
    
    # Cache miss - fetch from Airtable
    try:
        table = tables["votes"]
        formula = match({"project": project_id})
        records = table.all(formula=formula)
        
        votes = []
        for record in records:
            # Inject id from record["id"]
            fields = {**record["fields"], "id": record["id"]}
            vote = Vote.model_validate(fields)
            votes.append(vote)
            
            # Populate cache with TTL
            try:
                VoteCache(pk=record["id"], **vote.dict()).save(ttl=_get_ttl())
            except Exception:
                pass
        
        return votes
    except Exception:
        return []


def invalidate_vote(vote_id: str):
    """Remove vote from cache (called by webhook)."""
    try:
        VoteCache.delete(vote_id)
    except Exception:
        pass


def upsert_vote(vote: Vote):
    """Update or insert vote in cache (called by webhook)."""
    try:
        VoteCache(pk=vote.id, **vote.dict()).save(ttl=_get_ttl())
    except Exception:
        pass


# ===== REFERRAL OPERATIONS =====

def get_referral(referral_id: str) -> Optional[Referral]:
    """Get referral by ID from cache or Airtable."""
    return _get_from_cache_or_airtable(
        ReferralCache, Referral, "referrals", referral_id
    )


def get_referrals_for_event(event_id: str) -> List[Referral]:
    """Get all referrals for an event using cache index."""
    try:
        cached_referrals = ReferralCache.find(ReferralCache.event == event_id).all()
        if cached_referrals:
            return [Referral(**r.dict()) for r in cached_referrals]
    except Exception:
        pass
    
    # Cache miss - fetch from Airtable
    try:
        table = tables["referrals"]
        formula = match({"event": event_id})
        records = table.all(formula=formula)
        
        referrals = []
        for record in records:
            # Inject id from record["id"]
            fields = {**record["fields"], "id": record["id"]}
            referral = Referral.model_validate(fields)
            referrals.append(referral)
            
            # Populate cache with TTL
            try:
                ReferralCache(pk=record["id"], **referral.dict()).save(ttl=_get_ttl())
            except Exception:
                pass
        
        return referrals
    except Exception:
        return []


def invalidate_referral(referral_id: str):
    """Remove referral from cache (called by webhook)."""
    try:
        ReferralCache.delete(referral_id)
    except Exception:
        pass


def upsert_referral(referral: Referral):
    """Update or insert referral in cache (called by webhook)."""
    try:
        ReferralCache(pk=referral.id, **referral.dict()).save(ttl=_get_ttl())
    except Exception:
        pass


# ===== DELETE OPERATIONS =====
# All deletes go through these wrappers to ensure cache/Airtable consistency

def delete_event(event_id: str):
    """
    Delete event from Airtable and invalidate cache.
    
    All event deletions should go through this function.
    """
    # Delete from Airtable first
    tables["events"].delete(event_id)
    
    # Invalidate cache
    invalidate_event(event_id)
    
    # Set tombstone to prevent refetch
    _set_tombstone("events", event_id)


def delete_project(project_id: str):
    """
    Delete project from Airtable and invalidate cache.
    
    All project deletions should go through this function.
    """
    # Delete from Airtable first
    tables["projects"].delete(project_id)
    
    # Invalidate cache
    invalidate_project(project_id)
    
    # Set tombstone to prevent refetch
    _set_tombstone("projects", project_id)


def delete_user(user_id: str):
    """
    Delete user from Airtable and invalidate cache.
    
    All user deletions should go through this function.
    """
    # Delete from Airtable first
    tables["users"].delete(user_id)
    
    # Invalidate cache
    invalidate_user(user_id)
    
    # Set tombstone to prevent refetch
    _set_tombstone("users", user_id)


def delete_vote(vote_id: str):
    """
    Delete vote from Airtable and invalidate cache.
    
    All vote deletions should go through this function.
    """
    # Delete from Airtable first
    tables["votes"].delete(vote_id)
    
    # Invalidate cache
    invalidate_vote(vote_id)
    
    # Set tombstone to prevent refetch
    _set_tombstone("votes", vote_id)


def delete_referral(referral_id: str):
    """
    Delete referral from Airtable and invalidate cache.
    
    All referral deletions should go through this function.
    """
    # Delete from Airtable first
    tables["referrals"].delete(referral_id)
    
    # Invalidate cache
    invalidate_referral(referral_id)
    
    # Set tombstone to prevent refetch
    _set_tombstone("referrals", referral_id)
