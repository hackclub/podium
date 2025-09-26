import uuid
import datetime

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
async def test_signup(app_public_url, browser_session):
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

        # Check if the user was created in the database - this is the primary test assertion
        created_user = db.user.get_user_by_email(email, db.user.UserPrivate)
        logger.info(
            f"Finished signup attempt for {email}: success={result.success}, message='{result.message}', steel_view={getattr(browser_session, 'viewer_url', '')}"
        )
        assert created_user is not None, "User was not created in the database"
        
        # Verify user details in database
        assert created_user.email == email, "User email should match"
        assert created_user.display_name == "Test User", "User display name should match"
        assert created_user.first_name == "Test", "User first name should match"
        assert created_user.last_name == "User", "User last name should match"
        assert created_user.phone == "1234567890", "User phone should match"
        assert created_user.street_1 == "123 Main St", "User street should match"
        assert created_user.city == "Anytown", "User city should match"
        assert created_user.state == "CA", "User state should match"
        assert created_user.zip_code == "12345", "User zip code should match"
        assert created_user.country == "United States", "User country should match"
        assert created_user.dob == datetime.date(2010, 1, 1), "User date of birth should match"
    finally:
        # Best-effort cleanup of the test user if it was created
        try:
            if 'created_user' in locals() and created_user:
                db.users.delete(created_user.id)
                logger.info(f"Deleted test user {email} ({created_user.id})")
        except Exception:
            # Avoid failing the test teardown due to cleanup errors
            logger.warning(f"Failed to delete test user for {email}")


