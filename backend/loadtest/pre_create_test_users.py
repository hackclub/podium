"""Pre-create test users for load testing to avoid Airtable bottleneck during tests."""

import requests
import time

BASE_URL = "http://localhost:8000"
NUM_USERS = 50

print(f"Creating {NUM_USERS} test users...")
tokens = []

for i in range(NUM_USERS):
    try:
        response = requests.post(
            f"{BASE_URL}/test/token",
            params={"email": f"permanent_loadtest_user_{i}@example.com"},
            timeout=30,
        )
        response.raise_for_status()
        token = response.json()["access_token"]
        tokens.append(token)
        if (i + 1) % 10 == 0:
            print(f"  Created {i + 1}/{NUM_USERS} users...")
        time.sleep(0.1)  # Gentle rate limiting
    except Exception as e:
        print(f"  Failed to create user {i}: {e}")

print(f"\nSuccessfully created {len(tokens)} users")
print(f"Add these to your loadtest as a constant pool:")
print(f"USER_TOKENS = {tokens[:5]}... # ({len(tokens)} total)")
