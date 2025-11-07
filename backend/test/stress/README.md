# Stress Tests

Simple stress testing for Podium API endpoints.

## Run

```bash
# Install dependencies
cd backend
uv sync --group dev

# Run tests
cd test/stress
python main.py [events] [users_per_event]
```

## Args

- `events` - number of events (default: 2)
- `users_per_event` - users per event (default: 5, min: 2)

Creates multiple events with multiple users. Each user creates a project, then votes on other users' projects.

**Uses real authentication:** Calls API endpoints for auth flow, with minimal backend function imports only for token generation.

## Concurrency

**Sequential phases:** User creation, event creation, project creation (setup phases)  
**Concurrent phase:** All users simultaneously execute workflows via `asyncio.gather()`

**Real user navigation patterns (from frontend code):**
- **Every page load:** GET /events/ (events layout)
- **Projects page:** GET /events/ + GET /projects/mine  
- **Event pages:** GET /events/id/{slug} + GET /events/{event_id}
- **Ranking page:** GET /events/{event_id}/projects?leaderboard=false
- **Leaderboard page:** GET /events/{event_id}/projects?leaderboard=true
- **Plus:** User updates, voting, admin actions

**Concurrency pattern:** All users execute identical workflows simultaneously  
**Effect:** Same endpoint hit by all N users at the same moment (maximum DB stress)  
**For 50 events × 20 users:** 1000 users hitting each endpoint simultaneously

## Review Checklist Coverage

✅ **Register for a new account** - POST /users/  
✅ **Login using magic link** - POST /request-login + GET /verify  
✅ **Create a new event** - POST /events/  
✅ **Create a project via wizard** - POST /projects/  
✅ **Enable voting and leaderboard** - Admin panel endpoints  
✅ **Navigate to join link** - POST /events/attend  
✅ **Navigate to event ranking page** - GET /events/{id}/projects  
✅ **Rank projects** - POST /events/vote  
✅ **View leaderboard** - GET /events/admin/{id}/leaderboard  
✅ **Update project** - PUT /projects/{id}  
✅ **View admin leaderboard** - GET /events/admin/{id}/leaderboard  
✅ **Remove the second user** - POST /events/admin/{id}/remove-attendee

## Endpoints Covered

**Auth:** POST /users/, GET /users/exists, POST /request-login, GET /verify, GET /users/current, PUT /users/current  
**Events:** POST /events/, GET /events/{id}, GET /events/id/{slug}, GET /events/, POST /events/attend  
**Projects:** POST /projects/, GET /projects/mine, GET /projects/{id}, PUT /projects/{id}  
**Voting:** POST /events/vote, GET /events/{id}/projects  
**Admin:** GET /events/admin/{id}, GET /events/admin/{id}/attendees, GET /events/admin/{id}/leaderboard, GET /events/admin/{id}/votes, GET /events/admin/{id}/referrals, POST /events/admin/{id}/remove-attendee

Examples:
```bash
python main.py           # 2 events, 5 users each
python main.py 3 8       # 3 events, 8 users each
```

## Output

- Console summary with real-time progress
- `stress_test_report.json` - detailed results and statistics
- `response_times.png` - response time graphs (with event/user counts)
- `endpoint_comparison.png` - endpoint comparison charts

## Cleanup

If tests are interrupted or cleanup fails, use the cleanup script to remove all stress test data:

```bash
cd backend
uv run python test/stress/cleanup.py
```

This will delete:
- All users with emails matching `*@stress-test.example.com`
- All events with "Stress Test Event" in the name
- All projects with "stress-test" in the repo URL
- All referrals with "stress_test" content
- Votes are skipped (will be cleaned by daily sweep)

**Note:** The cleanup script uses direct Airtable deletes (not cache.delete_entity) since it's a standalone utility for test data cleanup.