# Frequently Used Commands

Run before committing:
```bash
cd backend && uv run ruff check --fix && cd ../frontend && bun run svelte-check
```

Test backend:
```bash
cd backend && uv run pytest
```

Test frontend (E2E):
```bash
cd frontend && doppler run --config dev -- bunx playwright test
```

Note: Tests use worker-scoped authentication and run in parallel (4 workers)

Stress test (performance/load testing):
```bash
# Already installed with uv
cd backend && uv run locust -f loadtest/locustfile.py --headless -u 200 -r 50 -t 5m --host http://localhost:8000
```

**Ephemeral & self-cleaning** - Creates test data, runs load test, cleans up automatically.  
See `backend/loadtest/README.md` for detailed documentation.

## Security Notes

Test endpoints (`/test-token`, `/test/bootstrap`, `/test/cleanup`) require **both**:
1. Environment ≠ production (normalized check for "production" or "prod")
2. `enable_test_endpoints = true` in settings (defaults to `false`)

Run locally:
```bash
# Backend (from backend/)
doppler run --config dev -- uv run podium

# Frontend (from frontend/)  
bun dev
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

**`tests/utils/api.ts`**
- `getEventBySlug(api, token, slug)` - Fetch event data via API
- `slugify(name)` - Convert name to URL slug

## Writing Tests

### Best Practices
1. **Use `unique()` for all entity names** to avoid collisions
2. **Wait for API responses** with `clickAndWaitForApi()` or `waitForResponse()`
3. **Prefer `getByRole()` or data-testid** over brittle text selectors
4. **Add `.first()`** to ambiguous selectors to avoid strict mode violations
5. **Wait for list refreshes** after creation: `await page.waitForResponse(...GET /events...)`

### Example Test
```typescript
test('should create event', async ({ authedPage }, testInfo) => {
  const name = unique('My Event', testInfo);
  
  await authedPage.goto('/events/create');
  await authedPage.locator('#event_name').fill(name);
  await authedPage.locator('#event_description').fill('Description');
  
  await clickAndWaitForApi(
    authedPage, 
    authedPage.getByRole('button', { name: /create/i }), 
    '/events', 
    'POST'
  );
  
  await expect(authedPage.getByText('Event created successfully')).toBeVisible();
});
```

## Known Limitations

### SSR + localStorage Auth Mismatch
**Issue:** Protected SSR routes (like `/events/attend`) cannot access `localStorage` on initial server render. Tests that `goto()` these routes directly will see an unauthenticated page.

**Impact:** The following flows are currently untested:
- Event attendance (requires protected `/events/attend` route)
- Project creation (requires event attendance first)
- Complex multi-step flows involving SSR-protected pages

**Workarounds:**
1. Use client-side navigation where possible (click links vs `goto()`)
2. Test these flows manually or via backend API tests
3. Consider adding data-testid attributes for more reliable selectors

**Future Fix:** Implement cookie-based session auth that SSR can read, then tests can use `goto()` for any route.

## Test Files

- `core.spec.ts` - Core event creation and listing
- `auth.spec.ts` - Authentication and signup flows
- `wizard.spec.ts` - Onboarding wizard
- `permissions.spec.ts` - Permission checks

## Configuration

**Parallel Execution:** 4 workers, fully parallel
**Retries:** 1 retry locally, 2 in CI
**Logs:** Quiet mode, backend stdout suppressed
**Screenshots:** On failure only
**Traces:** On first retry

# Cache System (Zero-Touch Configuration)

**Adding fields to models requires ZERO cache code changes!**

The cache system auto-detects configuration from Pydantic models.

## Adding a New Field

Just add to your Pydantic model - that's it!

```python
class Event(BaseEvent):
    owner: SingleRecordField  # Auto-indexed, auto-mapped to owner_id
    sponsor: str = ""         # Works automatically
    capacity: int = 0         # Works automatically
```

The cache automatically:
- Stores and retrieves it
- Indexes it (if `SingleRecordField`)
- Maps to Airtable lookups (SingleRecordField → `*_id`)
- Normalizes/denormalizes correctly

## Field Type Guide

- **`SingleRecordField`** → Auto-indexed, auto-mapped to Airtable `{field}_id`
- **`MultiRecordField`** → Stored as-is, not indexed
- **`Field(json_schema_extra={"indexed": True})`** → Indexed for queries
- **`Field(json_schema_extra={"sortable": True})`** → Sortable in cache
- **Scalar fields (str, int, bool)** → Just work, no config needed

## Cache Architecture

See [`backend/CACHING.md`](backend/CACHING.md) for complete details.

Key components:
- `cache/auto_config.py` - Auto-detects configuration from models
- `cache/operations.py` - Generic cache operations (get_one, get_by_index, etc.)
- `cache/specs.py` - Entity registry (auto-configured)
- `constants.py` - `SingleRecordField` with built-in indexing metadata

---

# Podium: Full System Overview and Architecture Report

This document provides a comprehensive overview of Podium: its purpose, architecture, subsystems, data model, flows, operational concerns, and development practices. All file references link to exact files and where useful, specific lines.

## Purpose and Product Summary

- Podium is a peer-judging platform for hackathons. Attendees submit projects, explore other submissions, and vote; organizers manage events, attendance, and see leaderboards.
- High-level user journeys (from the root docs): see the attendee and organizer overviews in the repository top-level README at [README.md](file:///home/augie/Code/hackclub/podium/README.md#L1-L35).
- Architecture summary: SvelteKit frontend + FastAPI backend; Airtable is the backing datastore; email auth via magic links; voting determines leaderboards; optional automated project checks via a separate “Review Factory” service.

## High-level Architecture

```mermaid
flowchart LR
  subgraph FE[SvelteKit Frontend]
    FE_UI[Routes, Components, State]\nTailwind/DaisyUI\nSentry (client)]
    FE_SDK[OpenAPI Client (@hey-api)]
  end

  subgraph BE[FastAPI Backend]
    Uvicorn[Uvicorn]
    Routers[Auth, Users, Events, Projects, Admin]
    Pydantic[Pydantic Models]
    Cache[fastapi-cache2 (InMemory)]
    SentryBE[Sentry (server)]
  end

  subgraph DS[Airtable]
    UsersTbl[Users]
    EventsTbl[Events]
    ProjectsTbl[Projects]
    VotesTbl[Votes]
    ReferralsTbl[Referrals]
  end

  subgraph Ext[External Services]
    SendGrid[SendGrid]
    ReviewFactory[Review Factory API]
  end

  FE_UI <--> FE_SDK
  FE_SDK <--> Uvicorn
  Routers <--> DS
  Routers -.-> SendGrid
  Routers -.-> ReviewFactory
  BE -. telemetry .-> SentryBE
  FE_UI -. telemetry .-> Sentry
```

- Backend entrypoint and router wiring: [`podium/main.py`](file:///home/augie/Code/hackclub/podium/backend/podium/main.py#L24-L56) dynamically includes all routers under `podium/routers` and enables CORS for all origins.
- Airtable tables are bound on import in [`db/db.py`](file:///home/augie/Code/hackclub/podium/backend/podium/db/db.py#L14-L30) using IDs in [`backend/settings.toml`](file:///home/augie/Code/hackclub/podium/backend/settings.toml#L1-L7).
- Secrets and config are managed by Dynaconf in [`podium/config.py`](file:///home/augie/Code/hackclub/podium/backend/podium/config.py#L9-L15), validated with `Validator`s.

## Backend

### Tech and Entry Points

- Runtime: Python 3.13, FastAPI, Uvicorn. Defined in [`pyproject.toml`](file:///home/augie/Code/hackclub/podium/backend/pyproject.toml#L9-L31) with `podium` console script mapping to [`__main__.py`](file:///home/augie/Code/hackclub/podium/backend/podium/__main__.py#L1-L4) → [`main`](file:///home/augie/Code/hackclub/podium/backend/podium/main.py#L62-L69).
- Sentry server SDK is initialized in [`main.py`](file:///home/augie/Code/hackclub/podium/backend/podium/main.py#L14-L21) with PII collection enabled in non-development environments.
- CORS: open to all (`*`) for headers/methods/origins (see [`main.py`](file:///home/augie/Code/hackclub/podium/backend/podium/main.py#L32-L40)).
- Caching: fastapi-cache2 InMemory initialized on lifespan ([`main.py`](file:///home/augie/Code/hackclub/podium/backend/podium/main.py#L24-L30)).

### Configuration and Secrets

- Config source: Dynaconf reading `settings.toml` and `.secrets.toml` with envvar prefix `PODIUM_` ([`config.py`](file:///home/augie/Code/hackclub/podium/backend/podium/config.py#L9-L15)).
- Required/validated keys include Airtable IDs/tokens, JWT settings, SendGrid key, Review Factory URL/token ([`config.py`](file:///home/augie/Code/hackclub/podium/backend/podium/config.py#L16-L75)).
- Non-secret IDs and defaults live in [`settings.toml`](file:///home/augie/Code/hackclub/podium/backend/settings.toml#L1-L19). Use `.secrets.toml` or env vars for secrets (see top-level [README.md](file:///home/augie/Code/hackclub/podium/README.md#L57-L65)).

### Data Layer (Airtable + Valkey Cache)

- Tables are attached on import in [`db/db.py`](file:///home/augie/Code/hackclub/podium/backend/podium/db/db.py#L14-L30) under the global `tables` dict: `events`, `users`, `projects`, `referrals`, `votes`.
- **Cache layer**: Valkey/Redis (redis-om) provides cache-aside pattern with 8hr TTL, webhook invalidation, and daily sweep. See [`cache/`](file:///home/sonder/Documents/Coding/showcase/backend/podium/cache) and [CACHING.md](file:///home/sonder/Documents/Coding/showcase/backend/CACHING.md).
  - **Strategy**: Cache full PrivateEvent/UserPrivate, derive public views on read. Eliminates dual-update issues.
  - **Invalidation**: Airtable automations POST to `/api/webhooks/airtable` on record changes.
  - **Deletion handling**: Use `cache.delete_*()` functions (not `db.*.delete()`) for atomic Airtable+cache+tombstone updates.
  - **Orphan cleanup**: Daily sweep with reference checking (90%+ Airtable API reduction vs naive approach).
- Pydantic models define schema, validation, and serialization for all entities:
  - Events: [`db/event.py`](file:///home/augie/Code/hackclub/podium/backend/podium/db/event.py#L11-L81)
  - Projects: [`db/project.py`](file:///home/augie/Code/hackclub/podium/backend/podium/db/project.py#L8-L67)
  - Users: [`db/user.py`](file:///home/augie/Code/hackclub/podium/backend/podium/db/user.py#L16-L83)
  - Votes: [`db/vote.py`](file:///home/augie/Code/hackclub/podium/backend/podium/db/vote.py#L6-L25)
  - Referrals: [`db/referral.py`](file:///home/augie/Code/hackclub/podium/backend/podium/db/referral.py#L5-L14)
- Common constants and typed aliases (e.g., record ID shapes, URL fields, slugs) in [`constants.py`](file:///home/augie/Code/hackclub/podium/backend/podium/constants.py#L7-L21).

### Authentication and Authorization

- Email-only magic link login:
  - Request link: [`POST /request-login`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/auth.py#L84-L93) sends a magic link via SendGrid (if configured) with token type `magic_link` ([`auth.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/auth.py#L52-L71)).
  - Verify token: [`GET /verify`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/auth.py#L101-L127) exchanges the magic link token for an `access` JWT.
  - Access control guard: [`get_current_user`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/auth.py#L134-L157) decodes/validates JWTs and loads the user from Airtable.
  - Token-type separation prevents using magic link tokens as access tokens ([`auth.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/auth.py#L36-L49)).
- Authorization is enforced at route-level by checking ownership or attendance as appropriate (examples: event update/delete require ownership in [`events.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/events.py#L160-L176); project update/delete require ownership in [`projects.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/projects.py#L129-L136)).

### Routers and Core APIs

- Auth: [`routers/auth.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/auth.py)
  - `POST /request-login` (magic link), `GET /verify` (issue access token).
- Users: [`routers/users.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/users.py)
  - `GET /users/exists?email=` – check existence ([`users.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/users.py#L29-L33)).
  - `GET /users/current`, `PUT /users/current` – get/update own profile ([`users.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/users.py#L36-L67)).
  - `GET /users/{id}` – public profile with cache ([`users.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/users.py#L73-L87)).
  - `POST /users/` – sign up (prevents duplicates) ([`users.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/users.py#L90-L97)).
- Events: [`routers/events.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/events.py)
  - Public: `GET /events/{id}` ([`events.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/events.py#L30-L46)); `GET /events/id/{slug}` ([`events.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/events.py#L315-L331)).
  - Authenticated user: `GET /events/` returns owned and attending lists ([`events.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/events.py#L49-L71)).
  - Create with unique slug + join code, owner set automatically ([`events.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/events.py#L74-L113)).
  - Attend by join code and record referral ([`events.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/events.py#L114-L148)).
  - Update/delete require ownership ([`events.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/events.py#L151-L177)).
  - Voting: `POST /events/vote` – enforces attendance, per-event max votes, no self-votes, one vote per project ([`events.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/events.py#L180-L249)).
  - Projects for event: random order vs leaderboard order with cache ([`events.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/events.py#L279-L312)).
- Admin (event owner only): [`routers/admin.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/admin.py)
  - `GET /events/admin/{event_id}` – private event object (includes join code etc.).
  - `GET /events/admin/{event_id}/attendees` – attendee details.
  - `POST /events/admin/{event_id}/remove-attendee` – remove attendee.
  - `GET /events/admin/{event_id}/leaderboard` – sorted projects by points.
  - `GET /events/admin/{event_id}/votes` – raw votes.
  - `GET /events/admin/{event_id}/referrals` – referral notes.
- Projects: [`routers/projects.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/projects.py)
  - `GET /projects/mine` – owned and collaborations ([`projects.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/projects.py#L25-L41)).
  - `POST /projects/` – create with unique join code; must attend the event ([`projects.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/projects.py#L44-L85)).
  - `POST /projects/join` – join via project join code; must attend the event ([`projects.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/projects.py#L87-L117)).
  - `PUT /projects/{id}` and `DELETE /projects/{id}` – owner-only ([`projects.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/projects.py#L119-L150)).
  - `GET /projects/{id}` – public project by ID ([`projects.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/projects.py#L153-L164)).
  - Automated project checks (Review Factory): start/poll endpoints ([`projects.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/projects.py#L168-L229)).

### Voting Rules and Leaderboard Logic

- Per-event vote cap computed dynamically by project count: 1 (<4 projects), 2 (4–19), 3 (≥20) via [`Event.max_votes_per_user`](file:///home/augie/Code/hackclub/podium/backend/podium/db/event.py#L35-L53).
- Vote constraints enforced in the voting endpoint:
  - Must be attending the event ([`events.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/events.py#L197-L200)).
  - Project must belong to the event ([`events.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/events.py#L216-L219)).
  - No duplicate votes for same project ([`events.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/events.py#L231-L240)).
  - No voting for own or collaborator projects ([`events.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/events.py#L242-L246)).
  - Enforces max per-user votes using Airtable `match` formulas ([`events.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/events.py#L223-L229)).

### Automated Project Checks (Review Factory)

- Models generated into [`generated/review_factory_models.py`](file:///home/augie/Code/hackclub/podium/backend/podium/generated/review_factory_models.py) via `datamodel-code-generator`.
- Start check: [`POST /projects/check/start`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/projects.py#L168-L206). If cached results exist on the project (`cached_auto_quality`), they are returned immediately.
- Poll check: [`GET /projects/check/{check_id}`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/projects.py#L208-L228).
- Requires `review_factory_token` in settings ([`settings.toml`](file:///home/augie/Code/hackclub/podium/backend/settings.toml#L19-L19) default; secret value in `.secrets.toml`).

### Error Handling, Constants, and Caching

- Shared HTTP exceptions/constants: [`constants.py`](file:///home/augie/Code/hackclub/podium/backend/podium/constants.py#L23-L33).
- Response caching used on selected endpoints with namespaces and TTL, e.g. users and events ([`users.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/users.py#L73-L87), [`events.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/events.py#L279-L291)).

### Deployment and Ops

- Docker: multi-stage with `uv` for dependency resolution; installs Playwright (for eval/test). See [`Dockerfile`](file:///home/augie/Code/hackclub/podium/backend/Dockerfile#L1-L16).
- Procfile for PaaS (e.g. Heroku/Fly): [`Procfile`](file:///home/augie/Code/hackclub/podium/backend/Procfile#L1-L1).
- docker-compose provides healthcheck and mounts config secrets ([`docker-compose.yaml`](file:///home/augie/Code/hackclub/podium/backend/docker-compose.yaml#L4-L18)).

### Tests (Browser-driven, Experimental)

- Test suite uses Steel SDK, Playwright, ngrok to drive a browser against the running app; primarily integration/e2e style. See the notes in [`backend/test/README.md`](file:///home/augie/Code/hackclub/podium/backend/test/README.md#L1-L37).

## Frontend

### Tech and Setup

- SvelteKit (Svelte 5, runes), Vite, Tailwind/DaisyUI, Sentry. Package config in [`package.json`](file:///home/augie/Code/hackclub/podium/frontend/package.json#L5-L12, file:///home/augie/Code/hackclub/podium/frontend/package.json#L13-L29, file:///home/augie/Code/hackclub/podium/frontend/package.json#L30-L38).
- Adapter: Vercel adapter in [`svelte.config.js`](file:///home/augie/Code/hackclub/podium/frontend/svelte.config.js#L2-L3, file:///home/augie/Code/hackclub/podium/frontend/svelte.config.js#L17-L21).
- Vite config integrates Sentry and allows ngrok hosts for dev tunneling ([`vite.config.js`](file:///home/augie/Code/hackclub/podium/frontend/vite.config.js#L7-L14, file:///home/augie/Code/hackclub/podium/frontend/vite.config.js#L15-L22)).

### API Client and OpenAPI

- The backend serves OpenAPI; the frontend generates a typed client via `@hey-api/openapi-ts`, configured in [`openapi-ts.config.ts`](file:///home/augie/Code/hackclub/podium/frontend/openapi-ts.config.ts#L4-L15) to pull from `http://localhost:8000/openapi.json`.
- Generated client and types live in [`src/lib/client`](file:///home/augie/Code/hackclub/podium/frontend/src/lib/client/sdk.gen.ts#L6-L6, file:///home/augie/Code/hackclub/podium/frontend/src/lib/client/types.gen.ts#L1-L8) and are consumed uniformly across the app.
- Runtime configuration is set in `hooks.client.ts` based on `PUBLIC_API_URL` and updates Authorization headers on login ([`hooks.client.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/hooks.client.ts#L22-L32)).

### Authentication Flow (Frontend)

- On client init, if a token is already present (state or localStorage), validate it by asking the backend for current user ([`hooks.client.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/hooks.client.ts#L33-L50)).
- Login/Signup page implements:
  - `GET /users/exists` to decide between login and signup ([`login/+page.svelte`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/login/+page.svelte#L43-L61)).
  - `POST /users/` for signup and `POST /request-login` to send magic link ([`login/+page.svelte`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/login/+page.svelte#L90-L114, file:///home/augie/Code/hackclub/podium/frontend/src/routes/login/+page.svelte#L64-L88)).
  - `GET /verify?token=` to exchange for access token; persists token then revalidates and redirects ([`login/+page.svelte`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/login/+page.svelte#L116-L141)).
- Client-side user state and helpers: [`src/lib/user.svelte.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/lib/user.svelte.ts#L32-L41, file:///home/augie/Code/hackclub/podium/frontend/src/lib/user.svelte.ts#L53-L81).

### Core User Journeys

- Dashboard/Home: prompts login or shows account summary and “Start Wizard” ([`routes/+page.svelte`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/+page.svelte#L21-L33, file:///home/augie/Code/hackclub/podium/frontend/src/routes/+page.svelte#L41-L63)).
- Events index: lists attending and owned events (with join code) and quick access to owner actions ([`events/+page.svelte`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/events/+page.svelte#L13-L21, file:///home/augie/Code/hackclub/podium/frontend/src/routes/events/+page.svelte#L53-L61, file:///home/augie/Code/hackclub/podium/frontend/src/routes/events/+page.svelte#L72-L90)). Data is loaded in [`events/+layout.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/events/+layout.ts#L15-L32) and unauthorized access returns 401 ([`events/+layout.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/events/+layout.ts#L34-L46)).
- Event page: “Rank Projects” (voting) and “Leaderboard” with gated availability ([`events/[slug]/+page.svelte`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/events/%5Bslug%5D/+page.svelte#L8-L23)).
- Event layout loader resolves slug aliases, reuses user’s events if available, or fetches public event if not ([`events/[slug]/+layout.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/events/%5Bslug%5D/+layout.ts#L16-L26, file:///home/augie/Code/hackclub/podium/frontend/src/routes/events/%5Bslug%5D/+layout.ts#L38-L67)).
- Voting page: shows eligible projects (excludes owned/collab/already voted), computes remaining votes, submits [`POST /events/vote`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/events/%5Bslug%5D/rank/+page.ts#L25-L33, file:///home/augie/Code/hackclub/podium/frontend/src/routes/events/%5Bslug%5D/rank/+page.svelte#L67-L76, file:///home/augie/Code/hackclub/podium/frontend/src/routes/events/%5Bslug%5D/rank/+page.svelte#L79-L83)).
- Leaderboard page: ordered list with points ([`leaderboard/+page.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/events/%5Bslug%5D/leaderboard/+page.ts#L9-L21, file:///home/augie/Code/hackclub/podium/frontend/src/routes/events/%5Bslug%5D/leaderboard/+page.svelte#L16-L25)).
- Attend event: join by code (and optional referral), supports auto-join via `?join_code=` link ([`AttendEvent.svelte`](file:///home/augie/Code/hackclub/podium/frontend/src/lib/components/AttendEvent.svelte#L12-L20, file:///home/augie/Code/hackclub/podium/frontend/src/lib/components/AttendEvent.svelte#L37-L49)).
- Project creation & membership:
  - Create project with event selection and field validation; respects event’s demo links optional flag ([`CreateProject.svelte`](file:///home/augie/Code/hackclub/podium/frontend/src/lib/components/CreateProject.svelte#L39-L64, file:///home/augie/Code/hackclub/podium/frontend/src/lib/components/CreateProject.svelte#L127-L143)).
  - Join project via join code (auto-join via link also supported) ([`JoinProject.svelte`](file:///home/augie/Code/hackclub/podium/frontend/src/lib/components/JoinProject.svelte#L17-L27, file:///home/augie/Code/hackclub/podium/frontend/src/lib/components/JoinProject.svelte#L37-L47)).
  - Projects page shows your projects, and asynchronously augments with automated quality results (see below) ([`projects/+page.svelte`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/projects/+page.svelte#L36-L44, file:///home/augie/Code/hackclub/podium/frontend/src/routes/projects/+page.svelte#L22-L29)).

### Automated Project Checks (Frontend)

- `checkProjectQuality` starts a check, returns cached results immediately if available, otherwise polls to completion ([`src/lib/async.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/lib/async.ts#L45-L63, file:///home/augie/Code/hackclub/podium/frontend/src/lib/async.ts#L6-L19)).
- Results are attached to each project’s UI on mount in the projects page ([`projects/+page.svelte`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/projects/+page.svelte#L22-L29)).

### UI Components and Styling

- Styling uses Tailwind v4 and DaisyUI, with theme switching support and curated theme set ([`consts.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/lib/consts.ts#L15-L26)).
- Components of note:
  - `ProjectCard` lazily fetches and displays contributor display names via `GET /users/{id}` ([`ProjectCard.svelte`](file:///home/augie/Code/hackclub/podium/frontend/src/lib/components/ProjectCard.svelte#L17-L41)).
  - Event Admin Panel bundles owner actions and tables (attendees, leaderboard, votes, referrals), with safeguards like “cannot remove yourself” ([`AdminPanel.svelte`](file:///home/augie/Code/hackclub/podium/frontend/src/lib/components/event-admin/AdminPanel.svelte#L102-L121)).
  - “Start Wizard” guides users through attending an event and creating/joining a project ([`StartWizard.svelte`](file:///home/augie/Code/hackclub/podium/frontend/src/lib/components/StartWizard.svelte#L6-L14, file:///home/augie/Code/hackclub/podium/frontend/src/lib/components/StartWizard.svelte#L28-L41)).
- Error handling and UX feedback centralized via `handleError` and `svelte-sonner` toasts ([`misc.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/lib/misc.ts#L11-L33)).

### Sentry (Frontend)

- Initialized in [`hooks.client.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/hooks.client.ts#L10-L20) with replay integration disabled for normal sessions; default PII sending disabled.
- Optional server-side Sentry hooks are present but commented in [`hooks.server.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/hooks.server.ts#L1-L16).

## Data Model

- Users
  - Private vs Public models: private includes contact and relationships, public only `display_name` ([`types.gen.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/lib/client/types.gen.ts#L229-L249, file:///home/augie/Code/hackclub/podium/frontend/src/lib/client/types.gen.ts#L251-L253)).
  - Lookups: relationships maintained via Airtable record IDs; helpers exist to fetch users by record IDs ([`db/user.py`](file:///home/augie/Code/hackclub/podium/backend/podium/db/user.py#L93-L104)).
- Events
  - Public event includes id, slug, owner, and computed `max_votes_per_user` ([`db/event.py`](file:///home/augie/Code/hackclub/podium/backend/podium/db/event.py#L26-L53)).
  - Private event extends with `attendees`, `join_code`, `projects`, `referrals`, `owned` flag ([`db/event.py`](file:///home/augie/Code/hackclub/podium/backend/podium/db/event.py#L56-L70)).
- Projects
  - Include `owner`, `collaborators`, `votes`, `points` (for leaderboards), and optional cached automated quality ([`db/project.py`](file:///home/augie/Code/hackclub/podium/backend/podium/db/project.py#L41-L55)).
- Votes
  - Store `project`, `event`, `voter`, and derived convenience fields for formula queries ([`db/vote.py`](file:///home/augie/Code/hackclub/podium/backend/podium/db/vote.py#L15-L21)).
- Referrals
  - Collected upon event join to capture acquisition info ([`db/referral.py`](file:///home/augie/Code/hackclub/podium/backend/podium/db/referral.py#L5-L12)).

## Security and Privacy Considerations

- JWT token types separated between `magic_link` and `access` to prevent misuse ([`auth.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/auth.py#L36-L49)).
- Authorization checks gate all modifications and sensitive reads to owners/attendees (examples above).
- CORS is currently permissive (`*`); lock down if deploying with strict origins ([`main.py`](file:///home/augie/Code/hackclub/podium/backend/podium/main.py#L32-L40)).
- Sentry
  - Backend: PII enabled outside development ([`main.py`](file:///home/augie/Code/hackclub/podium/backend/podium/main.py#L14-L21)). Ensure DSN/secrets are in the right environment and review data collection.
  - Frontend: PII disabled; replay configured for on-error sampling ([`hooks.client.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/hooks.client.ts#L10-L20)).
- Email delivery via SendGrid; be mindful of rate limiting and verification (see [`auth.py`](file:///home/augie/Code/hackclub/podium/backend/podium/routers/auth.py#L62-L75)).

## Performance and Caching

- In-memory caching via fastapi-cache2 for frequently read endpoints (users, event projects). Consider a distributed backend cache in multi-instance deployments.
- Client-side `invalidateAll()` + user revalidation on critical actions to keep UX consistent ([`misc.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/lib/misc.ts#L69-L74)).

## Local Development

- Frontend
  - From repo root: see [README.md](file:///home/augie/Code/hackclub/podium/README.md#L41-L47). Typical flow:
    ```bash
    cd frontend
    bun install
    bun dev
    ```
  - Set `PUBLIC_API_URL` in `frontend/.env` to point to backend.
- Backend
  - From repo root: see [README.md](file:///home/augie/Code/hackclub/podium/README.md#L49-L55). Typical flow:
    ```bash
    cd backend
    uv sync
    uv run podium
    ```
  - Provide secrets via environment or `backend/.secrets.toml`. Required keys listed in [README.md](file:///home/augie/Code/hackclub/podium/README.md#L57-L65) and validated in [`config.py`](file:///home/augie/Code/hackclub/podium/backend/podium/config.py#L16-L75).
  - Airtable base/table IDs are preconfigured for default and development in [`settings.toml`](file:///home/augie/Code/hackclub/podium/backend/settings.toml#L1-L19).
  - If using automated project checks locally, also run the Review Factory service and set `review_factory_token`.
- OpenAPI client generation (frontend):
  ```bash
  cd frontend
  bun run openapi-ts
  ```
  Config lives at [`openapi-ts.config.ts`](file:///home/augie/Code/hackclub/podium/frontend/openapi-ts.config.ts#L4-L15).

## Deployment Notes

- Backend: Docker instructions in [`Dockerfile`](file:///home/augie/Code/hackclub/podium/backend/Dockerfile#L1-L16) and PaaS `Procfile` ([`Procfile`](file:///home/augie/Code/hackclub/podium/backend/Procfile#L1-L1)). Mount `settings.toml` and `.secrets.toml` or provide env vars (compose example at [`docker-compose.yaml`](file:///home/augie/Code/hackclub/podium/backend/docker-compose.yaml#L15-L18)).
- Frontend: SvelteKit adapter for Vercel in [`svelte.config.js`](file:///home/augie/Code/hackclub/podium/frontend/svelte.config.js#L2-L3, file:///home/augie/Code/hackclub/podium/frontend/svelte.config.js#L17-L21); Sentry sourcemaps configured in Vite ([`vite.config.js`](file:///home/augie/Code/hackclub/podium/frontend/vite.config.js#L7-L14)).

## Design Rationale and Trade-offs

- Airtable as a datastore allows non-engineering stakeholders to inspect and adjust data quickly. The code embraces Airtable’s record ID-centric relationships and uses PyAirtable formulas for server-side validation and queries.
- Magic-link email login lowers friction for student users and avoids password management complexity; token-type separation mitigates risks.
- Generated OpenAPI client guarantees frontend-backend type alignment and reduces manual API client code.
- In-memory caching is simple and adequate for small deployments/events; can be upgraded to a distributed cache later.

## Notable Conventions and Patterns

- Parameter validation via Pydantic Annotated constraints (e.g., regex for Airtable record IDs) lives centrally in [`constants.py`](file:///home/augie/Code/hackclub/podium/backend/podium/constants.py#L11-L21) and throughout models.
- Ownership and attendance checks guard all mutating endpoints; vote logic is centralized and defensive.
- Frontend wraps all API interactions through the generated `EventsService`, `ProjectsService`, `UsersService`, `AuthService` classes ([`sdk.gen.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/lib/client/sdk.gen.ts#L8-L31, file:///home/augie/Code/hackclub/podium/frontend/src/lib/client/sdk.gen.ts#L33-L196, file:///home/augie/Code/hackclub/podium/frontend/src/lib/client/sdk.gen.ts#L198-L284, file:///home/augie/Code/hackclub/podium/frontend/src/lib/client/sdk.gen.ts#L286-L338)).
- Error handling centralized with `handleError` and Svelte navigation invalidations to keep UI state fresh ([`misc.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/lib/misc.ts#L11-L33, file:///home/augie/Code/hackclub/podium/frontend/src/lib/misc.ts#L71-L74)).

## Potential Improvements and Risks

- CORS: consider restricting allowed origins in production.
- Caching: replace InMemory with Redis/Memcached for multi-instance deployment (fastapi-cache2 supports memcache).
- Rate limiting: consider rate limit on auth endpoints (`/request-login`) to protect SendGrid and prevent abuse.
- Input validation: URLs are treated as strings; consider stronger validation for project/demo URLs.
- Sentry PII (backend) review, especially for production.
- Tests: browser-driven tests are valuable but slow; consider adding unit tests for router logic in addition.

## File Index (Key Files)

- Top-level overview and dev setup: [README.md](file:///home/augie/Code/hackclub/podium/README.md)
- Backend
  - App entry: [`podium/main.py`](file:///home/augie/Code/hackclub/podium/backend/podium/main.py)
  - Config: [`podium/config.py`](file:///home/augie/Code/hackclub/podium/backend/podium/config.py)
  - Airtable tables: [`podium/db/db.py`](file:///home/augie/Code/hackclub/podium/backend/podium/db/db.py)
  - Routers: [`podium/routers`](file:///home/augie/Code/hackclub/podium/backend/podium/routers)
  - Models: [`podium/db`](file:///home/augie/Code/hackclub/podium/backend/podium/db)
  - Settings: [`backend/settings.toml`](file:///home/augie/Code/hackclub/podium/backend/settings.toml)
- Frontend
  - App layout and hooks: [`src/routes/+layout.svelte`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/+layout.svelte), [`src/hooks.client.ts`](file:///home/augie/Code/hackclub/podium/frontend/src/hooks.client.ts)
  - Auth page: [`src/routes/login/+page.svelte`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/login/+page.svelte)
  - Events pages: [`src/routes/events`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/events)
  - Projects pages: [`src/routes/projects`](file:///home/augie/Code/hackclub/podium/frontend/src/routes/projects)
  - OpenAPI client: [`src/lib/client`](file:///home/augie/Code/hackclub/podium/frontend/src/lib/client)

---

This report is intended to be the authoritative architecture and behavior overview for Podium. Update alongside major feature or API changes to keep it current.
