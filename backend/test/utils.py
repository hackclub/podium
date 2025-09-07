import logging
import uuid
from typing import Mapping, Any, Dict, List, Optional
from datetime import timedelta
from loguru import logger

# Import these conditionally to avoid import errors when running utils.py directly
try:
    from podium import db
    from podium.routers import auth as auth_router
except ImportError:
    db = None
    auth_router = None

def magic_url(temp_user_tokens: Mapping[str, Any]) -> str:
    """Return a preformatted instruction containing the Steel magic login link."""
    logger.info(f"Magic login link: {temp_user_tokens['magic_link_url']}")
    return f"Use this magic login link to sign in: {temp_user_tokens['magic_link_url']}."


def create_temp_user_tokens(app_public_url: str) -> Dict[str, str]:
    """
    Create a temporary user directly in the DB, generate a short-lived access token
    and a magic-link token for browser login. Returns a dict with keys:
    - email, user_id, access_token, magic_link_token, magic_link_url

    Note: This function does NOT clean up the user - that should be handled by the caller.
    """
    if db is None or auth_router is None:
        raise ImportError("Required modules (podium.db, podium.routers.auth) not available")
    
    # match email format from test_login.py
    email = f"testuser-{uuid.uuid4()}@example.com"
    user_details = {
        "display_name": "Test User",
        "email": email,
        "first_name": "Test",
        "last_name": "User",
        "phone": "1234567890",
        "street_1": "123 Main St",
        "city": "Anytown",
        "state": "CA",
        "zip_code": "12345",
        "country": "United States",
        # store in ISO format as expected by backend serialization
        "dob": "2010-01-01",
    }
    
    # Create user
    created = db.users.create(user_details)
    created_user_id = created["id"]
    
    # Generate tokens
    access_token = auth_router.create_access_token(
        data={"sub": email}, expires_delta=timedelta(minutes=30), token_type="access"
    )
    magic_link_token = auth_router.create_access_token(
        data={"sub": email}, expires_delta=timedelta(minutes=15), token_type="magic_link"
    )
    magic_link_url = f"{app_public_url}/login?token={magic_link_token}"

    return {
        "email": email,
        "user_id": created_user_id,
        "access_token": access_token,
        "magic_link_token": magic_link_token,
        "magic_link_url": magic_link_url,
    }


def verify_event_exists(event_id: str, expected_name: str, expected_owner: str) -> bool:
    """Verify that an event exists in the database with the expected properties."""
    if db is None:
        raise ImportError("podium.db not available")
    
    try:
        event = db.events.get(event_id)
        return (
            event["fields"]["name"] == expected_name and
            expected_owner in event["fields"].get("owner", [])
        )
    except Exception:
        return False


def verify_user_in_event_attendees(event_id: str, user_id: str) -> bool:
    """Verify that a user is in the attendees list of an event."""
    if db is None:
        raise ImportError("podium.db not available")
    
    try:
        event = db.events.get(event_id)
        return user_id in event["fields"].get("attendees", [])
    except Exception:
        return False


def verify_user_exists(user_id: str, expected_email: str) -> bool:
    """Verify that a user exists in the database with the expected email."""
    if db is None:
        raise ImportError("podium.db not available")
    
    try:
        user = db.users.get(user_id)
        return user["fields"]["email"] == expected_email
    except Exception:
        return False


def verify_project_exists(project_id: str, expected_event_id: str, expected_owner: str) -> bool:
    """Verify that a project exists in the database with the expected properties."""
    if db is None:
        raise ImportError("podium.db not available")
    
    try:
        project = db.projects.get(project_id)
        return (
            expected_event_id in project["fields"].get("event", []) and
            expected_owner in project["fields"].get("owner", [])
        )
    except Exception:
        return False


def verify_vote_exists(vote_id: str, expected_event_id: str, expected_project_id: str, expected_voter: str) -> bool:
    """Verify that a vote exists in the database with the expected properties."""
    if db is None:
        raise ImportError("podium.db not available")
    
    try:
        vote = db.votes.get(vote_id)
        return (
            expected_event_id in vote["fields"].get("event", []) and
            expected_project_id in vote["fields"].get("project", []) and
            expected_voter in vote["fields"].get("voter", [])
        )
    except Exception:
        return False


def get_event_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """Get an event by its slug."""
    if db is None:
        raise ImportError("podium.db not available")
    
    try:
        from pyairtable.formulas import match
        return db.events.first(formula=match({"slug": slug}))
    except Exception:
        return None


def assert_event_created(event_name: str, expected_owner: str, expected_description: str = None) -> str:
    """Assert that an event was created and return its ID."""
    if db is None:
        raise ImportError("podium.db not available")
    
    from slugify import slugify
    slug = slugify(event_name, lowercase=True, separator="-")
    event = get_event_by_slug(slug)
    
    assert event is not None, f"Event '{event_name}' was not created in database"
    assert event["fields"]["name"] == event_name, f"Event name mismatch: expected '{event_name}', got '{event['fields']['name']}'"
    assert expected_owner in event["fields"].get("owner", []), f"User {expected_owner} is not the owner of event"
    
    if expected_description is not None:
        assert event["fields"]["description"] == expected_description, f"Event description mismatch: expected '{expected_description}', got '{event['fields']['description']}'"
    
    return event["id"]


def assert_user_joined_event(event_id: str, user_id: str) -> None:
    """Assert that a user joined an event."""
    assert verify_user_in_event_attendees(event_id, user_id), f"User {user_id} was not added as attendee to event {event_id}"


def assert_user_created(email: str, expected_details: Dict[str, Any]) -> str:
    """Assert that a user was created and return their ID."""
    if db is None:
        raise ImportError("podium.db not available")
    
    user_id = db.user.get_user_record_id_by_email(email)
    assert user_id is not None, f"User with email '{email}' was not created in database"
    
    user_record = db.users.get(user_id)
    for field, expected_value in expected_details.items():
        actual_value = user_record["fields"].get(field)
        assert actual_value == expected_value, f"User {field} mismatch: expected '{expected_value}', got '{actual_value}'"
    
    return user_id


if __name__ == "__main__":
    # When run directly, create a temporary user and output the magic link
    import os
    
    # Get the app public URL from environment or use a default
    try:
        from test.config import APP_PORT
        default_url = f"http://localhost:{APP_PORT}"
    except ImportError:
        default_url = "http://localhost:5173"
    
    app_public_url = os.environ.get("APP_PUBLIC_URL", default_url)
    
    try:
        tokens = create_temp_user_tokens(app_public_url)
        print(f"Magic Link: {tokens['magic_link_url']}")
        
    except ImportError as e:
        print(f"Error: {e}")
        print("Make sure you're running this from the backend directory with the proper environment.")
        print("Try: cd backend && python -m test.utils")
    except Exception as e:
        print(f"Error creating temporary user: {e}")
        logger.exception("Failed to create temporary user")


