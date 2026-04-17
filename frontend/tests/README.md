# E2E Tests

Playwright tests split between UI-focused journey specs and an API-level coverage
spec that guarantees every backend endpoint is exercised at least once.

## Run tests

Stop any running dev servers first (they collide on ports 8000 and 4173):

```bash
pkill -f podium; pkill -f "vite|bun.*dev"
```

Then from `frontend/`:

```bash
doppler run --config dev -- npx playwright test                  # full suite
doppler run --config dev -- npx playwright test tests/api-coverage.spec.ts
doppler run --config dev -- npx playwright test --ui             # interactive mode
```

Doppler injects `PODIUM_JWT_SECRET`, `PODIUM_DATABASE_URL`, and other backend
env vars. Playwright boots both servers on demand (see `playwright.config.ts`).

## Files

| File | Purpose |
| --- | --- |
| `auth.spec.ts` | Signup form UI |
| `core.spec.ts` | Official events list, attend, wizard, event detail, leaderboard link |
| `wizard.spec.ts` | Project submission wizard routing |
| `permissions.spec.ts` | Admin panel visibility + leaderboard access |
| `journey.spec.ts` | Full hackathon UI journey (organizer → attendee → vote → admin) |
| `api-coverage.spec.ts` | **Every backend endpoint hit at least once via direct API calls** |

Helpers: `helpers/api.ts` (endpoint wrappers), `helpers/users.ts` (secondary
user setup), `helpers/jwt.ts` (magic-link JWT signing), `fixtures/auth.ts`
(worker-scoped authed page + API contexts), `utils/data.ts` (`unique()` for
collision-free data across workers).

## Coverage guarantee

`api-coverage.spec.ts` is the source of truth for endpoint coverage. When you
add a route to `backend/podium/routers/`, add a matching test there. The file
is organised by router (auth / users / events / projects / admin / test) so
the mapping stays obvious.

`GET /verify` and `POST /users/` are implicitly exercised by the per-worker
auth fixture before any other test runs.

## Backend test endpoints

Two endpoints only exist when `enable_test_endpoints=true`:

- `POST /events/test/create` — creates an event in VOTING phase; used by every
  spec that needs an event.
- `POST /events/test/cleanup` — reaps data for any user whose email matches
  `test+pw*@example.com`, `organizer+*@test.local`, `attendee+*@test.local`,
  or `admin+*@test.local`. Invoke it manually between local runs if the DB
  gets cluttered; we don't call it from tests because it would stomp on
  parallel workers.

## Parallelism

Four workers, fully parallel. Tests isolate state by using unique emails per
worker (`test+pw{workerIndex}@example.com`) and timestamp-suffixed names for
events and projects (see `utils/data.ts`). Secondary users created inside a
test get a timestamp+worker tag so parallel runs don't collide.
