# Architecture

Podium is a peer-judging platform for Hack Club hackathons. Attendees select an official event, submit projects, and vote.

## Stack

- **Frontend:** SvelteKit (Svelte 5), Tailwind, DaisyUI
- **Backend:** FastAPI, SQLModel (async PostgreSQL)
- **Auth:** Magic link email via Loops API
- **Cache:** Redis (optional — leaderboards cached 30s; app works without it)
- **CAPTCHA:** Cloudflare Turnstile on unauthenticated endpoints
- **Monitoring:** Sentry

## Data Model

Core entities:

- **User** — email, display_name, first_name, is_superadmin
- **Event** — name, slug, phase, feature_flags_csv, repo_validation, demo_validation, require_address
- **Project** — name, repo, image_url, demo, owner_id, event_id, points, validation_status, validation_message
- **Vote** — voter_id, project_id, event_id (unique on voter+project)

M2M relationships via junction tables:
- `event_attendees` — User ↔ Event
- `project_collaborators` — User ↔ Project

## Event Lifecycle

Events move through phases in order: `draft` → `submission` → `voting` → `closed`.

| Phase | What's allowed |
|---|---|
| `draft` | Not yet visible to users |
| `submission` | Users can join and submit projects |
| `voting` | Submissions closed; users can vote |
| `closed` | Voting closed; leaderboard visible |

The phase is changed by the event owner via the admin panel UI or `PATCH /events/admin/{id}`.

## Event Series

Events are grouped into a **series** — a flagship event plus its satellites (e.g., "Scrapyard 2025"). Only one series is active at a time, controlled by `ACTIVE_EVENT_SERIES` in backend config. Events with matching `feature_flags_csv` appear in the event selector.

Key rules:
- **One event per user per series** — backend enforces; selecting a new event auto-switches
- **Events are admin-created** — users select from a list, never create events
- **All official events are equal** — no UI distinction between flagship and satellites
- **Past series are read-only** — users can view but not edit old projects

## Validation System

Background validation runs after every project create/update — never blocks the user. Results are informational badges (`pending → valid | warning`).

Validation is configured per-event via `repo_validation` and `demo_validation` fields:

| Setting | What it does |
|---|---|
| `repo_validation: github` | Checks repo exists and is public via GitHub API |
| `demo_validation: itch` | Checks itch.io page has `.game_frame` (browser-playable) |
| `repo_validation: custom` | Calls the named entry in `validators/custom/` |
| `none` | Skips validation for that field |

Events can also set `require_address: true` to enforce that users have a shipping address on file before submitting — this is a hard block at the API level.

## User Flow

```
Sign in → Select event → (Address check) → Submit project → Validation → Vote
```

1. User signs in via magic link
2. Selects from available official events (`GET /events/official`)
3. If `require_address` is set, must provide shipping address first
4. Creates or joins a project (join codes allow collaborators)
5. Background validation runs; badge appears on project card
6. Can vote on other projects

## Voting Rules

Vote limits scale with project count: 1 vote (< 4 projects), 2 votes (4-19), 3 votes (≥ 20). Users can't vote for their own or collaborated projects.

## Key Directories

Backend (`backend/podium/`):
- `main.py` — FastAPI app, lifespan (Redis init/close)
- `config.py` — Dynaconf settings (all env vars with `PODIUM_` prefix)
- `constants.py` — Shared types: `EventPhase`, `RepoValidation`, `DemoValidation`, `BAD_AUTH`, etc.
- `limiter.py` — slowapi rate limiter (user-email based)
- `db/postgres/` — SQLModel models and database session helpers
- `routers/` — API endpoints (`auth`, `users`, `events`, `projects`, `admin`, `superadmin`)
- `validators/` — Project URL validation: `github.py`, `itch.py`, `custom/` (event-specific); input validation: `email.py`, `turnstile.py`
- `cache/` — Redis helpers (`cache_get`, `cache_set`, `cache_delete`) with graceful no-op fallback

Frontend (`frontend/src/`):
- `hooks.client.ts` — Client init, auth validation
- `lib/client/` — Generated OpenAPI client (run `bun run openapi-ts` to regenerate)
- `lib/forms/` — Reusable form components (Button, Input, Label, Textarea, FileDropZone)
- `lib/logos/` — Event logo components (CampfireFlagship, CampfireSat)
- `lib/user.svelte.ts` — User state
- `lib/validation.ts` — Project validation
- `routes/` — SvelteKit pages

## Admin Tools

- `backend/scripts/manage_events.py` — TUI: create events, manage attendees, toggle superadmin, delete users/events
- `POST /superadmin/events` — API: create real events (requires `is_superadmin`)
- `PATCH /events/admin/{id}` — API: update any event field (owners and superadmins)
- NocoDB — spreadsheet UI for the database (see nocodb.md)

Superadmin status (`is_superadmin`) is toggled via the TUI Users tab — there is no API for it.
