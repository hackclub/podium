"""Authentication utilities for stress testing."""

import sys
import os
from datetime import timedelta
from typing import Dict, Any, Optional

# Add the backend directory to the Python path
backend_dir = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, backend_dir)

try:
    from podium.routers.auth import create_access_token
    AUTH_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import auth functions: {e}")
    AUTH_AVAILABLE = False


def create_magic_link_token(email: str) -> Optional[str]:
    """Create a valid magic link token for testing (ONLY for bypassing email)."""
    if not AUTH_AVAILABLE:
        return None
    
    try:
        token_data = {"sub": email}
        token = create_access_token(
            data=token_data, 
            expires_delta=timedelta(minutes=15), 
            token_type="magic_link"
        )
        return token
    except Exception as e:
        print(f"Error creating magic link token: {e}")
        return None


async def simulate_auth_flow_via_api(client, email: str) -> Optional[Dict[str, Any]]:
    """Simulate auth flow using API endpoints where possible."""
    try:
        # 1. Request magic link via API
        login_payload = {"email": email}
        login_response = await client.post("/request-login?redirect=", json=login_payload)
        
        if login_response.status_code != 200:
            print(f"Magic link request failed for {email}: {login_response.status_code}")
            return None
        
        # 2. Generate magic link token (only import backend function for this)
        magic_token = create_magic_link_token(email)
        if not magic_token:
            print("Could not generate magic link token")
            return None
        
        # 3. Verify magic link via API to get access token
        verify_response = await client.get(f"/verify?token={magic_token}")
        
        if verify_response.status_code == 200:
            verify_data = verify_response.json()
            return {
                "access_token": verify_data["access_token"],
                "magic_token": magic_token,
                "user_data": verify_data["user"]
            }
        else:
            print(f"Token verification failed for {email}: {verify_response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error in API auth flow: {e}")
        return None
