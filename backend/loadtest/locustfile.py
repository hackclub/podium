"""
Podium Stress Test - Multi-Event Concurrent Load Simulation

Simulates realistic usage patterns across multiple concurrent hackathon events:
- Attendees who create/join projects and vote
- Lurkers who browse but don't participate
- Organizers who monitor leaderboards

Run examples:
    # Basic test with 5 events, 200 users (40 per event)
    locust -f loadtest/locustfile.py --headless -u 200 -r 50 -t 10m --host http://localhost:8000 --csv run_results

    # Cache-buster mode to stress test Airtable directly
    CACHE_BUSTER=true locust -f loadtest/locustfile.py --headless -u 200 -r 50 -t 10m --host http://localhost:8000

    # Higher concurrency for stress testing
    locust -f loadtest/locustfile.py --headless -u 500 -r 100 -t 15m --host http://localhost:8000

Configuration via environment variables:
    BASE_URL - Backend API base URL (default: http://localhost:8000)
    EVENTS - Number of concurrent events to simulate (default: 5)
    VOTE_BURST_OFFSET - Seconds after test start to begin vote window (default: 180)
    VOTE_BURST_DURATION - Duration of voting window in seconds (default: 180)
"""

from locust import HttpUser, task, between, events
import os
import random
import time
from typing import Optional, Set

# Configuration from environment
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
EVENTS = int(os.getenv("EVENTS", "5"))
VOTE_OFFSET = int(os.getenv("VOTE_BURST_OFFSET", "180"))  # 3 minutes
VOTE_DURATION = int(os.getenv("VOTE_BURST_DURATION", "180"))  # 3 minutes

# Global test state
RUN_ID = str(int(time.time()))
TEST_START = time.time()
EVENT_IDS = []
EVENT_METADATA = {}  # Maps event_id -> {slug, join_code, name}

# Metrics tracking
cache_hits = 0
cache_misses = 0
rate_429s = 0


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Bootstrap test events via /test/bootstrap endpoint."""
    global EVENT_IDS, EVENT_METADATA
    print(f"\n[START] Starting Podium stress test (run ID: {RUN_ID})")
    print(f"   Simulating {EVENTS} concurrent events")
    print(f"   Vote window: {VOTE_OFFSET}s - {VOTE_OFFSET + VOTE_DURATION}s\n")
    
    # Bootstrap test data via API
    import requests
    try:
        response = requests.post(
            f"{BASE_URL}/test/bootstrap",
            json={
                "run_id": RUN_ID,
                "events": EVENTS,
                "seed_projects_per_event": 3,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        
        # Store event metadata
        for event in data["events"]:
            EVENT_METADATA[event["id"]] = {
                "slug": event["slug"],
                "join_code": event["join_code"],
                "name": event["name"],
            }
        
        # Use event record IDs as identifiers
        EVENT_IDS = list(EVENT_METADATA.keys())
        event_names = [event["slug"] for event in data["events"]]
        print(f"[BOOTSTRAP] Created {len(EVENT_IDS)} events and seed projects")
        print(f"   Events: {', '.join(event_names)}\n")
    except Exception as e:
        print(f"[ERROR] Failed to bootstrap test data: {e}")
        print(f"   Falling back to placeholder event IDs\n")
        EVENT_IDS = [f"lt-{RUN_ID}-{i}" for i in range(EVENTS)]


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, exception, **kw):
    """Track cache hit/miss rates and 429 responses."""
    global cache_hits, cache_misses, rate_429s
    
    if response is not None:
        # Track X-Cache header if present
        xc = response.headers.get("X-Cache", "").upper()
        if xc == "HIT":
            cache_hits += 1
        elif xc == "MISS":
            cache_misses += 1
        
        # Track rate limiting
        if response.status_code == 429:
            rate_429s += 1


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print final statistics and cleanup test data."""
    total_cache_checks = cache_hits + cache_misses
    hit_rate = (cache_hits / total_cache_checks * 100) if total_cache_checks > 0 else 0
    
    print(f"\n\n[STATS] Final Statistics (Run ID: {RUN_ID})")
    print(f"   Cache hits: {cache_hits}")
    print(f"   Cache misses: {cache_misses}")
    print(f"   Hit rate: {hit_rate:.1f}%")
    print(f"   429 Responses: {rate_429s}")
    print(f"   Events tested: {len(EVENT_IDS)}\n")
    
    # Cleanup test data
    import requests
    try:
        print(f"[CLEANUP] Removing test data for run {RUN_ID}...")
        response = requests.post(
            f"{BASE_URL}/test/cleanup",
            json={"run_id": RUN_ID},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"[CLEANUP] Deleted:")
        print(f"   Events: {data['deleted_events']}")
        print(f"   Projects: {data['deleted_projects']}")
        print(f"   Votes: {data['deleted_votes']}")
        print(f"   Referrals: {data['deleted_referrals']}")
        print(f"   Users: {data['deleted_users']}")
        if data.get('errors'):
            print(f"[CLEANUP] Errors: {len(data['errors'])}")
            for err in data['errors'][:5]:  # Show first 5 errors
                print(f"   - {err}")
        print(f"[CLEANUP] Complete - no test data left behind\n")
    except Exception as e:
        print(f"[WARN] Cleanup failed: {e}")
        print(f"   Manual cleanup may be required for run {RUN_ID}\n")


def in_vote_window() -> bool:
    """Check if we're currently in the voting burst window."""
    elapsed = time.time() - TEST_START
    return VOTE_OFFSET <= elapsed <= (VOTE_OFFSET + VOTE_DURATION)


def get_bearer_token(email: str, client) -> str:
    """Get auth token using test endpoint."""
    try:
        response = client.post(
            f"{BASE_URL}/test/token",
            params={"email": email},
            name="/test/token"
        )
        if response.status_code == 200:
            return f"Bearer {response.json()['access_token']}"
        else:
            print(f"Auth failed for {email}: /test/token returned {response.status_code}")
            print(f"  Make sure PODIUM_ENABLE_TEST_ENDPOINTS=true is set")
            return "Bearer invalid"
    except Exception as e:
        print(f"Auth failed for {email}: {e}")
        return "Bearer invalid"


class BasePodiumUser(HttpUser):
    """Base user with common functionality."""
    wait_time = between(0.5, 2.0)
    abstract = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.email: str = ""
        self.headers: dict = {}
        self.event_id: str = ""
        self.event_join_code: str = ""
        self.own_projects: Set[str] = set()
        self.joined_projects: Set[str] = set()
        self.voted_projects: Set[str] = set()
        self.max_votes: int = 3  # Default, will be updated from event
        self.all_event_projects: list = []
        self.initialized = False
    
    def on_start(self):
        """Initialize user - authenticate and pick an event."""
        # Generate unique email for this user
        self.email = f"user_{RUN_ID}_{random.randint(1, 10**9)}@loadtest.com"
        
        # Authenticate
        self.headers = {"Authorization": get_bearer_token(self.email, self.client)}
        
        # Pick a random event to participate in
        self.event_id = random.choice(EVENT_IDS)
        
        # Attend the event using join code
        attended = False
        if self.event_id in EVENT_METADATA:
            join_code = EVENT_METADATA[self.event_id]["join_code"]
            with self._make_request(
                "POST",
                "/events/attend",
                params={"join_code": join_code, "referral": "Load test"},
                name="/events/attend"
            ) as response:
                if response.status_code in [200, 409]:  # 409 = already attending
                    attended = True
                else:
                    print(f"Failed to attend event {self.event_id}: {response.status_code}")
        
        if attended:
            with self.get(f"/events/{self.event_id}", name="/events/:id") as response:
                if response.status_code == 200:
                    try:
                        event_data = response.json()
                        self.max_votes = event_data.get("max_votes_per_user", self.max_votes)
                    except Exception:
                        pass

        self.initialized = attended  # Only initialize if successfully attended
    
    def _make_request(self, method, path, name=None, params=None, json=None):
        """Make HTTP request."""
        return self.client.request(
            method,
            path,
            headers=self.headers,
            name=name or path,
            params=params,
            json=json,
            catch_response=True
        )
    
    def get(self, path, name=None, params=None):
        """Make GET request."""
        return self._make_request("GET", path, name, params)
    
    def post(self, path, json=None, name=None):
        """Make POST request."""
        return self._make_request("POST", path, name, json=json)
    
    def _browse_projects(self, *, leaderboard=False, update_cache=None, label=None):
        """Fetch event projects with optional leaderboard view and caching."""
        if not self.initialized:
            return False

        query = "true" if leaderboard else "false"
        request_name = label or ("/events/:id/projects (leaderboard)" if leaderboard else "/events/:id/projects")
        should_update_cache = update_cache if update_cache is not None else not leaderboard

        with self.get(
            f"/events/{self.event_id}/projects?leaderboard={query}",
            name=request_name
        ) as response:
            if response.status_code == 200 and should_update_cache:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        self.all_event_projects = data
                except Exception:
                    pass
            return response.status_code == 200

    def fetch_event_projects(self):
        """Fetch all projects for the user's event."""
        self._browse_projects()
    
    def get_random_project_id(self) -> Optional[str]:
        """Get a random project ID from the event."""
        if not self.all_event_projects:
            self.fetch_event_projects()
        
        if not self.all_event_projects:
            return None
        
        project = random.choice(self.all_event_projects)
        return project.get("id")
    
    def check_leaderboard(self):
        """Check event leaderboard (sorted projects)."""
        self._browse_projects(leaderboard=True, update_cache=False)


class Attendee(BasePodiumUser):
    """
    Active participant (70% of users):
    - Creates or joins a project once
    - Browses projects
    - Votes during vote window
    - Checks leaderboard
    """
    weight = 70
    
    @task(5)
    def browse_projects(self):
        """Browse event projects."""
        self._browse_projects()
    
    @task(3)
    def view_project_detail(self):
        """View a specific project."""
        if not self.initialized:
            return
        
        project_id = self.get_random_project_id()
        if project_id:
            self.get(f"/projects/{project_id}", name="/projects/:id")
    
    @task(1)
    def create_or_join_project(self):
        """Create or join a project (only once)."""
        if not self.initialized or self.own_projects or self.joined_projects:
            return
        
        # Create project (skip join - requires join_code which isn't exposed)
        project_name = f"Project_{RUN_ID}_{random.randint(1, 10**9)}"
        with self.post(
            "/projects/",
            json={
                "name": project_name,
                "description": f"Load test project for {self.event_id}",
                "event": [self.event_id],  # Must be a list of record IDs
                "repo": "https://github.com/example/repo",  # Required
                "image_url": "https://example.com/image.png",  # Required
                "demo": "https://example.com/demo",  # Include to avoid validation issues
            },
            name="/projects [create]"
        ) as response:
            if response.status_code in [200, 201]:
                try:
                    project_id = response.json().get("id")
                    if project_id:
                        self.own_projects.add(project_id)
                except Exception:
                    pass
    
    @task(8)
    def vote_for_project(self):
        """Vote for projects during vote window."""
        if not self.initialized:
            return
        
        # Only vote during vote window
        if not in_vote_window():
            return
        
        # Check if we've reached vote limit
        if len(self.voted_projects) >= self.max_votes:
            return
        
        # Get a project to vote for
        project_id = self.get_random_project_id()
        
        # Skip if already voted or it's our own project
        if not project_id or project_id in self.voted_projects or project_id in self.own_projects:
            return
        
        # Cast vote
        with self.post(
            f"/events/{self.event_id}/vote",
            json={"project_id": project_id},
            name="/events/:id/vote"
        ) as response:
            if response.status_code == 200:
                self.voted_projects.add(project_id)
                # Check leaderboard after voting (typical behavior)
                self.check_leaderboard()
            elif response.status_code in [409, 422]:
                # Expected constraint violations (already voted, self-vote, etc.)
                response.success()


class Lurker(BasePodiumUser):
    """
    Read-only user (25% of users):
    - Browses projects
    - Views project details
    - Checks leaderboard
    - Never creates, joins, or votes
    """
    weight = 25
    
    @task(6)
    def browse_projects(self):
        """Browse event projects."""
        self._browse_projects()
    
    @task(4)
    def view_project_detail(self):
        """View a specific project."""
        if not self.initialized:
            return
        
        project_id = self.get_random_project_id()
        if project_id:
            self.get(f"/projects/{project_id}", name="/projects/:id")
    
    @task(3)
    def browse_more_projects(self):
        """Browse projects more frequently."""
        self._browse_projects()


class Organizer(BasePodiumUser):
    """
    Event organizer (5% of users):
    - Hammers leaderboard during vote window (emcee behavior)
    - Browses projects occasionally
    - May check admin endpoints
    """
    weight = 5
    
    @task(8)
    def browse_projects_during_voting(self):
        """Browse projects frequently, especially during voting."""
        # Especially during vote window - use leaderboard=true to simulate organizer checking results
        if in_vote_window():
            self._browse_projects(leaderboard=True, update_cache=False, label="/events/:id/projects (leaderboard)")
        else:
            self._browse_projects(label="/events/:id/projects")
    
    @task(2)
    def browse_projects(self):
        """Occasionally browse projects."""
        self._browse_projects()
    
    @task(1)
    def check_admin_stats(self):
        """Check admin endpoints if available."""
        if not self.initialized:
            return
        
        # This might 403 if user isn't actually owner, which is fine
        with self.get(f"/events/admin/{self.event_id}", name="/events/admin/:id") as response:
            if response.status_code == 403:
                response.success()  # Expected for non-owners
