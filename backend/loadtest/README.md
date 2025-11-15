# Podium Stress Testing

Simulates realistic multi-event hackathon usage to test performance under load.

## Quick Start

```bash
# Start backend (test endpoints auto-enabled in development)
cd backend
doppler run --config dev -- uv run podium

# Run test (separate terminal)
cd backend
uv run locust -f loadtest/locustfile.py  --headless -u 200 -r 50 -t 5m --host http://localhost:8000
```

Note: `enable_test_endpoints = true` in `settings.toml` [development] section.

**Result:** Creates test events → simulates 200 users → cleans up everything → shows performance stats

## What It Does

- **Bootstrap**: Creates 5 test events with seed projects (tagged with run_id)
- **Simulate**: 200 users across 3 personas (Attendees 70%, Lurkers 25%, Organizers 5%)
- **Behaviors**: Browse projects, create projects, vote (during burst window at 3min mark)
- **Cleanup**: Deletes all events, projects, votes, referrals, users via name-based formulas
- **Report**: Response times, error rates, cache hit ratio

## How It Works

**Bootstrap** (`POST /test/bootstrap`):
- Creates events with slugs `lt-{run_id}-{i}` for discoverable cleanup
- Creates seed bot user and seed projects (gives users content immediately)
- Returns event IDs and join_codes to Locust

**Authentication** (`POST /test/token`):
- Bypasses magic link email flow
- Creates users with email `user_{run_id}_*@loadtest.com` for batch cleanup
- Returns standard JWT access tokens

**User Simulation**:
- Each user picks random event, authenticates, and attends
- Attendees (70%): Browse, create projects, vote during burst window
- Lurkers (25%): Browse and view projects only
- Organizers (5%): Aggressively check leaderboard during voting

**Cleanup** (`POST /test/cleanup`):
- Uses name-based Airtable formulas (linked fields expose text, not IDs)
- Deletes in dependency order: votes → projects → events → referrals → users
- Invalidates cache keys for deleted entities
- Returns deletion counts and any errors encountered

## Configuration

Environment variables:

```bash
# Number of concurrent events (default: 5)
EVENTS=10 uv run locust ...

# Voting burst timing (defaults: 180s offset, 180s duration)
VOTE_BURST_OFFSET=120 VOTE_BURST_DURATION=240 uv run locust ...

# Backend URL (default: http://localhost:8000)
BASE_URL=https://staging.api.podium.app uv run locust ...
```

## Test Modes

### Interactive (Web UI)
```bash
uv run locust -f loadtest/locustfile.py --host http://localhost:8000
# Open http://localhost:8089 to control the test
```

### High Load
```bash
EVENTS=10 uv run locust -f loadtest/locustfile.py \
  --headless -u 500 -r 100 -t 15m --host http://localhost:8000
```

## Understanding Results

**Response times** (shown as Avg/Med/p95 in table):
- Time from request to response in milliseconds
- Lower is faster

**Failure rate** (% in table):
- Percentage of requests that failed
- Shown per endpoint and aggregated

**Cache hit rate** (printed at end):
- Percentage of requests served from cache vs Airtable

**Error codes**:
- `200` = Success
- `403/409/422` = Validation/authorization errors
- `429` = Rate limited by Airtable
- `500/503` = Server error

## Locust Parameters

```bash
-u 200      # Total simulated users
-r 50       # Spawn rate (users/second)
-t 10m      # Test duration (s=seconds, m=minutes, h=hours)
--headless  # No web UI (just terminal output)
--csv X     # Save results to X_stats.csv, X_failures.csv, etc.
--host URL  # Backend URL
```

## Security

Test endpoints require both:
1. `env ≠ "production"` (normalized check for "production"/"prod")
2. `enable_test_endpoints = true` in settings (enabled in [development] section)

## Manual Cleanup

If test crashes before auto-cleanup runs:

```bash
curl -X POST http://localhost:8000/test/cleanup \
  -H "Content-Type: application/json" \
  -d '{"run_id": "RUN_ID_FROM_TEST_OUTPUT"}'
```
