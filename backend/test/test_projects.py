import uuid

import pytest
from loguru import logger
from pydantic import BaseModel
from pyairtable.formulas import match
from secrets import token_urlsafe
from slugify import slugify
from requests import HTTPError

from podium import db
from test.browser import run_browser_agent
from test.utils import magic_url


class SimpleResult(BaseModel):
    success: bool = False
    message: str = ""


def _unique_name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


@pytest.mark.asyncio
async def test_project_submission(app_public_url, browser_session, temp_user_tokens):
    created_event_id: str | None = None
    created_project_id: str | None = None

    # Prepare event to attend
    join_code = token_urlsafe(3).upper()
    event_name = _unique_name("Project Event")
    event_slug = slugify(event_name, lowercase=True, separator="-")
    created = db.events.create(
        {
            "name": event_name,
            "description": "Event for project submission",
            "join_code": join_code,
            "slug": event_slug,
            "owner": [],
            "attendees": [],
        }
    )
    created_event_id = created["id"]

    project_name = _unique_name("Project")
    project_desc = "Automated test project"
    repo_url = "https://example.com/repo"
    demo_url = "https://example.com/demo"

    try:
        # Join the event via UI, then create project via UI
        prompt = (
            f"{magic_url(temp_user_tokens)} "
            f"Join an event using this join code: {join_code}. "
            "Then create a new project in the app with these details: "
            f"name='{project_name}', description='{project_desc}', repo='{repo_url}', demo='{demo_url}'."
        )

        result = await run_browser_agent(
            prompt=prompt,
            output_model=SimpleResult,
            failure_result=SimpleResult(success=False, message="Failed"),
            browser=browser_session,
        )
        logger.info(
            f"Project submission result: success={result.success}, message='{result.message}', steel_view={getattr(browser_session, 'viewer_url', '')}"
        )

        # Verify project in DB
        record = db.projects.first(formula=match({"name": project_name}))
        assert record is not None, "Project was not created"
        created_project_id = record["id"]
        fields = record["fields"]
        assert temp_user_tokens["user_id"] in fields.get("owner", []), "User not owner of project"
        assert fields.get("event", []) == [created_event_id], "Project not linked to event"
    finally:
        if created_project_id:
            try:
                db.projects.delete(created_project_id)
            except Exception:
                logger.warning(f"Failed to delete project {created_project_id}")
        if created_event_id:
            try:
                db.events.delete(created_event_id)
            except Exception:
                logger.warning(f"Failed to delete event {created_event_id}")


@pytest.mark.asyncio
async def test_project_deletion(app_public_url, browser_session, temp_user_tokens):
    created_event_id: str | None = None
    project_id: str | None = None

    # Create event and add user as attendee
    event_name = _unique_name("Delete Event")
    event_slug = slugify(event_name, lowercase=True, separator="-")
    created_event = db.events.create(
        {
            "name": event_name,
            "description": "Event for project deletion",
            "join_code": token_urlsafe(3).upper(),
            "slug": event_slug,
            "owner": [],
            "attendees": [temp_user_tokens["user_id"]],
        }
    )
    created_event_id = created_event["id"]

    # Create project owned by user in that event
    project_name = _unique_name("To Delete")
    created_project = db.projects.create(
        {
            "name": project_name,
            "description": "Project to delete",
            "repo": "https://example.com/repo",
            "demo": "https://example.com/demo",
            "image_url": "",
            "event": [created_event_id],
            "owner": [temp_user_tokens["user_id"]],
            "collaborators": [],
            "join_code": token_urlsafe(3).upper(),
            "hours_spent": 0,
        }
    )
    project_id = created_project["id"]

    try:
        prompt = (
            f"{magic_url(temp_user_tokens)} "
            f"Find the project named '{project_name}' in your projects, open its edit UI, and delete it. "
            "Confirm if there's a prompt."
        )

        result = await run_browser_agent(
            prompt=prompt,
            output_model=SimpleResult,
            failure_result=SimpleResult(success=False, message="Failed"),
            browser=browser_session,
        )
        logger.info(
            f"Project deletion result: success={result.success}, message='{result.message}', steel_view={getattr(browser_session, 'viewer_url', '')}"
        )

        # Verify deletion
        with pytest.raises(HTTPError):
            _ = db.projects.get(project_id)
    finally:
        # Cleanup in case UI deletion failed
        if project_id:
            try:
                db.projects.delete(project_id)
            except Exception:
                pass
        if created_event_id:
            try:
                db.events.delete(created_event_id)
            except Exception:
                pass


