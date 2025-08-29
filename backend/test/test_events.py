import uuid

import pytest
from loguru import logger
from pydantic import BaseModel
from pyairtable.formulas import match
from secrets import token_urlsafe
from slugify import slugify

from podium import db
from test.browser import run_browser_agent
from test.utils import magic_url


class SimpleResult(BaseModel):
    success: bool = False
    message: str = ""


def _unique_name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


@pytest.mark.asyncio
# uv run pytest -s -k "test_event_creation"                                                                                                                                                                       
async def test_event_creation(app_public_url, browser_session, temp_user_tokens):
    created_event_id: str | None = None
    event_name = _unique_name("E2E Event")
    description = "An automated test event"

    prompt = (
        f"{magic_url(temp_user_tokens)} "
        "Create a new event in the app with these details and finish: "
        f"name='{event_name}', description='{description}'."
    )

    try:
        result = await run_browser_agent(
            prompt=prompt,
            output_model=SimpleResult,
            failure_result=SimpleResult(success=False, message="Failed"),
            browser=browser_session,
        )
        logger.info(
            f"Event creation result: success={result.success}, message='{result.message}', steel_view={getattr(browser_session, 'viewer_url', '')}"
        )

        # Verify event in DB
        slug = slugify(event_name, lowercase=True, separator="-")
        record = db.events.first(formula=match({"slug": slug}))
        assert record is not None, "Event was not created"
        created_event_id = record["id"]
        assert temp_user_tokens["user_id"] in record["fields"].get("owner", []), "User not owner of event"
    finally:
        if created_event_id:
            try:
                db.events.delete(created_event_id)
            except Exception:
                logger.warning(f"Failed to delete event {created_event_id}")


@pytest.mark.asyncio
async def test_event_joining(app_public_url, browser_session, temp_user_tokens):
    created_event_id: str | None = None
    join_code = token_urlsafe(3).upper()
    name = _unique_name("Joinable Event")
    slug = slugify(name, lowercase=True, separator="-")

    try:
        # Create an event to join
        created = db.events.create(
            {
                "name": name,
                "description": "Event for joining",
                "join_code": join_code,
                "slug": slug,
                "owner": [],
                "attendees": [],
            }
        )
        created_event_id = created["id"]

        prompt = (
            f"{magic_url(temp_user_tokens)} "
            f"Join the event using this join code: {join_code}."
        )

        result = await run_browser_agent(
            prompt=prompt,
            output_model=SimpleResult,
            failure_result=SimpleResult(success=False, message="Failed"),
            browser=browser_session,
        )
        logger.info(
            f"Event joining result: success={result.success}, message='{result.message}', steel_view={getattr(browser_session, 'viewer_url', '')}"
        )

        # Verify attendee added
        event = db.events.get(created_event_id)
        assert temp_user_tokens["user_id"] in event["fields"].get("attendees", []), "User not added as attendee"
    finally:
        if created_event_id:
            try:
                db.events.delete(created_event_id)
            except Exception:
                logger.warning(f"Failed to delete event {created_event_id}")


