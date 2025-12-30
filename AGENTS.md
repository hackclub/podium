# Frequently Used Commands

Run before committing:
```bash
cd backend && uv run ruff check --fix && cd ../frontend && bun run svelte-check
```

<!-- Test backend:
```bash
cd backend && uv run pytest
``` -->

Test frontend (E2E):
```bash
cd frontend && doppler run --config dev -- npx playwright test
```

Note: Tests use worker-scoped authentication and run in parallel (4 workers). Use npx (not bunx) for Playwright.

Run locally:
```bash
# Backend (from backend/)
doppler run --config dev -- uv run podium

# Frontend (from frontend/)  
bun dev
```

# Database

**PostgreSQL** via SQLModel (async). No caching layer needed.

Models in `backend/podium/db/postgres/`:
- `user.py`, `event.py`, `project.py`, `vote.py`, `referral.py`
- `links.py` - M2M junction tables (use surrogate PKs for Mathesar Extend compatibility)
- `base.py` - Session factory

**Database Views:**
- See `mathesar/VIEWS.md` for optional views (e.g., `users_with_events` for Airtable-like display)

## Local Postgres + Mathesar (Docker Compose)

```bash
# First time setup
cp .env.example .env
# Edit .env with DOPPLER_TOKEN (generate: doppler configs tokens create dev-local --config dev --max-age 1h --plain)

# Start
docker compose up -d

# Postgres: localhost:5432 (postgres/localpass)
# Mathesar: http://localhost:8000
```

For Coolify, use `mathesar/docker-compose.yaml` (connects to external `podium` network).

The `mathesar/bootstrap.py` script runs on container start to:
- Create admin user and database connection (if missing)
- Update stored credentials (always)
- Run `install_sql()` to install Mathesar's helper functions in Podium DB

## Reset Local Database

```bash
./scripts/reset-local-db.sh           # Reset and run migrations
./scripts/reset-local-db.sh --sync    # Reset, migrate, and sync from production
```

## Migrations

Run migrations:
```bash
cd backend && doppler run --config dev -- uv run alembic upgrade head
```

Generate migrations after model changes:
```bash
cd backend && doppler run --config dev -- uv run alembic revision --autogenerate -m "description"
```

# E2E Test Architecture

## Overview

The Playwright test suite covers core authenticated UI flows using client-side auth (localStorage). Tests run in parallel with 4 workers and worker-scoped authentication for speed and isolation.

## Running Tests

```bash
cd frontend && doppler run --config dev -- bunx playwright test

# Run specific test file
bunx playwright test core.spec.ts

# Run with UI mode
bunx playwright test --ui

# Run in headed mode (see browser)
bunx playwright test --headed
```

## Architecture

### Authentication (Worker-Scoped)
- Each worker gets a unique user: `test+pw{workerIndex}@example.com`
- JWT token obtained via backend API (`/verify` endpoint with magic link)
- Token injected into `localStorage` via Playwright `storageState`
- Token reused across all tests in the worker (fast!)

### Test Structure
```typescript
import { test, expect } from './fixtures/auth';
import { unique } from './utils/data';
import { clickAndWaitForApi } from './utils/waiters';

test('my test', async ({ authedPage, api }, testInfo) => {
  const name = unique('Entity', testInfo);
  // authedPage is pre-authenticated
  // api is APIRequestContext for backend calls
});
```

### Utilities

**`tests/fixtures/auth.ts`**
- `test` - Extended Playwright test with auth fixtures
- `authedPage` - Pre-authenticated page (token in localStorage)
- `api` - APIRequestContext for backend API calls
- `token` - JWT access token (available via `(authedPage as any)._authToken`)

**`tests/utils/waiters.ts`**
- `waitForApiOk(page, urlPart, method)` - Wait for API response
- `clickAndWaitForApi(page, locator, urlPart, method)` - Click + wait pattern

**`tests/utils/data.ts`**
- `unique(name, testInfo)` - Generate unique names: `{name}-{timestamp}-w{worker}-r{retry}`

**`tests/helpers/api.ts`**
- `createEvent(api, data)` - Create an event via API
- `attendEvent(api, joinCode, referral)` - Attend an event
- `createProject(api, data)` - Create a project
- `voteForProjects(api, eventId, projectIds)` - Cast votes
- `getLeaderboard(api, eventId)` - Get leaderboard

## Writing Tests

### Best Practices
1. **Use `unique()` for all entity names** to avoid collisions
2. **Wait for API responses** with `clickAndWaitForApi()` or `waitForResponse()`
3. **Prefer `getByRole()` or data-testid** over brittle text selectors
4. **Add `.first()`** to ambiguous selectors to avoid strict mode violations
5. **Wait for list refreshes** after creation: `await page.waitForResponse(...GET /events...)`

## Test Files

- `core.spec.ts` - Core event creation and listing
- `auth.spec.ts` - Authentication and signup flows
- `wizard.spec.ts` - Onboarding wizard
- `permissions.spec.ts` - Permission checks

## Configuration

**Parallel Execution:** 4 workers, fully parallel
**Retries:** 1 retry locally, 2 in CI
**Screenshots:** On failure only
**Traces:** On first retry

---

# Podium Architecture

## Purpose

Podium is a peer-judging platform for hackathons. Attendees submit projects, explore submissions, and vote. Organizers manage events, attendance, and leaderboards.

## Stack

- **Frontend:** SvelteKit (Svelte 5), Tailwind/DaisyUI, Sentry
- **Backend:** FastAPI, SQLModel (async PostgreSQL), Sentry
- **Auth:** Magic link email login via Loops API
- **External:** Review Factory (automated project checks)

## Data Model

- **User** - email, display_name, first_name, etc.
- **Event** - name, slug, join_code, owner_id, votable, leaderboard_enabled
- **Project** - name, repo, image_url, demo, owner_id, event_id, points
- **Vote** - voter_id, project_id, event_id (unique constraint on voter+project)
- **Referral** - content, user_id, event_id

M2M relationships:
- Event ↔ User (attendees) via `event_attendees`
- Project ↔ User (collaborators) via `project_collaborators`

## API Endpoints

### Auth
- `POST /request-login` - Send magic link
- `GET /verify` - Exchange magic link for access token

### Users
- `GET /users/exists?email=` - Check if user exists
- `GET /users/current` - Get current user
- `PUT /users/current` - Update current user
- `GET /users/{id}` - Get public user info
- `POST /users/` - Create user

### Events
- `GET /events/` - Get user's owned and attending events
- `GET /events/{id}` - Get public event
- `POST /events/` - Create event
- `POST /events/attend` - Join event with code
- `PUT /events/{id}` - Update event (owner only)
- `DELETE /events/{id}` - Delete event (owner only)
- `POST /events/vote` - Vote for projects
- `GET /events/{id}/projects` - Get event projects
- `GET /events/id/{slug}` - Get event ID by slug

### Projects
- `GET /projects/mine` - Get user's projects
- `GET /projects/{id}` - Get project
- `POST /projects/` - Create project
- `POST /projects/join` - Join project as collaborator
- `PUT /projects/{id}` - Update project (owner only)
- `DELETE /projects/{id}` - Delete project (owner only)
- `POST /projects/check/start` - Start quality check
- `GET /projects/check/{id}` - Poll check status

### Admin (Event owner only)
- `GET /events/admin/{id}` - Get private event
- `GET /events/admin/{id}/attendees` - List attendees
- `POST /events/admin/{id}/remove-attendee` - Remove attendee
- `GET /events/admin/{id}/leaderboard` - Get leaderboard
- `GET /events/admin/{id}/votes` - Get votes
- `GET /events/admin/{id}/referrals` - Get referrals

## Frontend OpenAPI Client

Types are auto-generated from backend OpenAPI schema:
```bash
cd frontend && bun run openapi-ts
```

Generated files in `src/lib/client/`:
- `sdk.gen.ts` - API client methods
- `types.gen.ts` - TypeScript types

## Voting Rules

- Max votes per user: 1 (< 4 projects), 2 (4-19), 3 (≥ 20)
- Cannot vote for own or collaborated projects
- Cannot vote for same project twice
- Must be attending the event

## File Index

### Backend
- `podium/main.py` - FastAPI app entry
- `podium/config.py` - Dynaconf settings
- `podium/db/postgres/` - SQLModel models
- `podium/routers/` - API endpoints
- `podium/constants.py` - Shared constants

### Frontend
- `src/hooks.client.ts` - Client init, auth validation
- `src/lib/client/` - Generated API client
- `src/lib/user.svelte.ts` - User state
- `src/routes/` - SvelteKit routes
