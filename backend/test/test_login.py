import uuid

from podium import db
import pytest
from loguru import logger
from pydantic import BaseModel
from test import settings
from test.browser import run_browser_agent


class SignupResult(BaseModel):
    success: bool = False
    message: str = ""


@pytest.mark.asyncio
async def test_login(app_public_url, browser_session):
    created_user_id: str | None = None
    # tell the agent to go signup with <uuid>@example.com, and then, check if the user was created in the database
    email = f"testuser-{uuid.uuid4()}@example.com"
    user_details = {
        "display_name": "Test User",
        # "email": email,
        "first_name": "Test",
        "last_name": "User",
        "phone": "1234567890",
        "street_1": "123 Main St",
        "city": "Anytown",
        "state": "CA",
        "zip": "12345",
        "country": "United States",
        "dob": "01/01/2010",
    }
    prompt = f"Create a user on {app_public_url} with the email {email} and the following details and then, exit: {user_details}"
    try:
        result = await run_browser_agent(
                prompt=prompt,
                output_model=SignupResult,
                failure_result=SignupResult(success=False, message="Failed to signup"),
                browser=browser_session,
                config=settings,
            )

        # Check if the user was created in the database
        created_user_id = db.user.get_user_record_id_by_email(email)
        logger.info(f"Finished signup attempt for {email} with result: {result}")
        assert created_user_id is not None, "User was not created in the database"
    finally:
        # Best-effort cleanup of the test user if it was created
        try:
            if created_user_id:
                db.users.delete(created_user_id)
                logger.info(f"Deleted test user {email} ({created_user_id})")
        except Exception:
            # Avoid failing the test teardown due to cleanup errors
            logger.warning(f"Failed to delete test user for {email}")