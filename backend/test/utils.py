import logging
import uuid
from typing import Mapping, Any, Dict
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


