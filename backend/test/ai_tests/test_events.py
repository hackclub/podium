import uuid

import pytest
from loguru import logger
from pydantic import BaseModel
from pyairtable.formulas import match
from secrets import token_urlsafe
from slugify import slugify

from podium import db
from test.ai_tests.browser import run_browser_agent
from test.ai_tests.utils import magic_url


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

        # Verify event in DB - this is the primary test assertion
        slug = slugify(event_name, lowercase=True, separator="-")
        record = db.events.first(formula=match({"slug": slug}))
        assert record is not None, "Event was not created in database"
        created_event_id = record["id"]

        # Verify event details
        assert record["fields"]["name"] == event_name, "Event name should match"
        assert record["fields"]["description"] == description, (
            "Event description should match"
        )
        assert temp_user_tokens["user_id"] in record["fields"].get("owner", []), (
            "User should be owner of event"
        )
        assert record["fields"]["slug"] == slug, "Event slug should be correct"

        # Verify the event can be retrieved by ID
        event_by_id = db.events.get(created_event_id)
        assert event_by_id["fields"]["name"] == event_name, (
            "Event should be retrievable by ID"
        )
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

        # Verify initial state - user should not be an attendee yet
        event_before = db.events.get(created_event_id)
        assert temp_user_tokens["user_id"] not in event_before["fields"].get(
            "attendees", []
        ), "User should not be attendee initially"
        assert event_before["fields"]["join_code"] == join_code, (
            "Join code should match"
        )

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

        # Verify attendee was added - this is the primary test assertion
        event_after = db.events.get(created_event_id)
        assert temp_user_tokens["user_id"] in event_after["fields"].get(
            "attendees", []
        ), "User should be added as attendee"

        # Verify other event details remain unchanged
        assert event_after["fields"]["name"] == name, (
            "Event name should remain unchanged"
        )
        assert event_after["fields"]["join_code"] == join_code, (
            "Join code should remain unchanged"
        )
        assert event_after["fields"]["slug"] == slug, (
            "Event slug should remain unchanged"
        )
    finally:
        if created_event_id:
            try:
                db.events.delete(created_event_id)
            except Exception:
                logger.warning(f"Failed to delete event {created_event_id}")
