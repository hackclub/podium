"""Webhook endpoints for cache invalidation."""

from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import hmac

from podium.config import settings
from podium.db.project import Project
from podium.db.event import Event, PrivateEvent
from podium.db.user import UserPrivate
from podium.db.vote import Vote
from podium.db.referral import Referral
from podium.cache.operations import (
    upsert_project,
    upsert_event,
    upsert_user,
    upsert_vote,
    upsert_referral,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class AirtableWebhookPayload(BaseModel):
    """Payload sent from Airtable automation."""
    table: str
    record: Dict[str, Any]
    record_id: str
    timestamp: str


@router.post("/airtable")
async def airtable_webhook(
    payload: AirtableWebhookPayload,
    request: Request,
    x_airtable_secret: Optional[str] = Header(None),
):
    """
    Receive webhook from Airtable automation and update cache.
    
    Called when records are created/updated in Airtable.
    Validates secret and upserts records into cache.
    """
    # Validate webhook secret using constant-time comparison (prevents timing attacks)
    expected_secret = getattr(settings, "airtable_webhook_secret", None)
    if not expected_secret:
        logger.warning("airtable_webhook_secret not configured in settings")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    
    if not hmac.compare_digest(x_airtable_secret or "", expected_secret):
        logger.warning(f"Invalid webhook secret from {request.client.host}")
        raise HTTPException(status_code=401, detail="Invalid secret")
    
    table_name = payload.table
    record_data = payload.record
    
    logger.info(f"Received webhook for table={table_name}, record_id={payload.record_id}")
    
    try:
        # Route to appropriate cache upsert function based on table
        if table_name == "Projects":
            project = Project.model_validate(record_data)
            upsert_project(project)
            logger.info(f"Updated cache for project {project.id}")
            
        elif table_name == "Events":
            # Try to parse as PrivateEvent (has more fields)
            try:
                event = PrivateEvent.model_validate(record_data)
            except Exception:
                # Fall back to regular Event
                event = Event.model_validate(record_data)
            upsert_event(event)
            logger.info(f"Updated cache for event {event.id}")
            
        elif table_name == "Users":
            user = UserPrivate.model_validate(record_data)
            upsert_user(user)
            logger.info(f"Updated cache for user {user.id}")
            
        elif table_name == "Votes":
            vote = Vote.model_validate(record_data)
            upsert_vote(vote)
            logger.info(f"Updated cache for vote {vote.id}")
            
        elif table_name == "Referrals":
            referral = Referral.model_validate(record_data)
            upsert_referral(referral)
            logger.info(f"Updated cache for referral {referral.id}")
            
        else:
            logger.warning(f"Unknown table: {table_name}")
            raise HTTPException(status_code=400, detail=f"Unknown table: {table_name}")
        
        return {
            "status": "success",
            "table": table_name,
            "record_id": payload.record_id,
            "message": "Cache updated"
        }
        
    except Exception as e:
        logger.error(f"Failed to process webhook for {table_name}: {e}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Failed to process record: {str(e)}")


@router.get("/health")
async def webhook_health():
    """Health check endpoint for cache invalidation service."""
    return {"status": "ok", "service": "cache_invalidation"}


if __name__ == "__main__":
    """
    Generate a secure webhook secret for Airtable automation.
    
    Usage:
        uv run podium.routers.cache_invalidate
    
    Copy the generated secret to:
    1. backend/.secrets.toml: airtable_webhook_secret = "..."
    2. Airtable "Invalidate Config" table: webhook_secret record
    """
    import secrets
    
    # Generate a cryptographically secure random secret (256 bits)
    secret = secrets.token_urlsafe(32)
    
    print("=" * 60)
    print("Generated Airtable Webhook Secret")
    print("=" * 60)
    print()
    print(f"Secret: {secret}")
    print()
    print("Configuration steps:")
    print()
    print("1. Add to backend/.secrets.toml:")
    print(f'   airtable_webhook_secret = "{secret}"')
    print()
    print("2. Add to Airtable 'Invalidate Config' table:")
    print("   key: webhook_secret")
    print(f"   value: {secret}")
    print()
    print("=" * 60)
