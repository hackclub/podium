"""Configuration for stress tests."""

import os
import time
import random

# API Configuration
API_BASE_URL = os.getenv("STRESS_TEST_API_URL", "http://localhost:8000")
API_TIMEOUT = 30  # seconds

# Test Configuration
NUM_EVENTS = 2
USERS_PER_EVENT = 5  # Must be at least 2 for voting
CLEANUP_AFTER_TESTS = True

# Test Data Configuration
TEST_EMAIL_DOMAIN = "stress-test.example.com"
TEST_NAME_PREFIX = "StressTest"

# Response time thresholds (in seconds)
SLOW_REQUEST_THRESHOLD = 2.0
VERY_SLOW_REQUEST_THRESHOLD = 5.0

def generate_unique_id() -> str:
    """Generate a unique identifier for test data."""
    timestamp = int(time.time() * 1000)
    random_suffix = random.randint(1000, 9999)
    return f"{timestamp}_{random_suffix}"

def generate_test_email(unique_id: str) -> str:
    """Generate a unique test email."""
    return f"test_{unique_id}@{TEST_EMAIL_DOMAIN}"

def generate_test_name(unique_id: str, prefix: str = TEST_NAME_PREFIX) -> str:
    """Generate a unique test name."""
    return f"{prefix}_{unique_id}"
