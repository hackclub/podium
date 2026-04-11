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

- **User** — email, display_name, first_name
- **Event** — name, slug, feature_flags_csv, phase
- **Project** — name, repo, image_url, demo, owner_id, event_id, points
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

The phase is changed by the event owner via the admin API (`PUT /events/admin/{id}` with `phase` field).

## Event Series

Events are grouped into a **series** — a flagship event plus its satellites (e.g., "Scrapyard 2025"). Only one series is active at a time, controlled by `ACTIVE_EVENT_SERIES` in backend config. Events with matching `feature_flags_csv` appear in the event selector.

Key rules:
- **One event per user per series** — backend enforces; selecting a new event auto-switches
- **Events are admin-created** — users select from a list, never create events
- **All official events are equal** — no UI distinction between flagship and satellites
- **Past series are read-only** — users can view but not edit old projects

## User Flow

```
Sign in → Select event → Submit project → Validation → Vote
```

1. User signs in via magic link
2. Selects from available official events (GET /events/official)
3. Creates or joins a project (project join codes still exist for collaborators)
4. Project validated (itch.io playability check)
5. Can vote on other projects

## Voting Rules

Vote limits scale with project count: 1 vote (< 4 projects), 2 votes (4-19), 3 votes (≥ 20). Users can't vote for their own or collaborated projects.

## Key Directories

Backend (`backend/podium/`):
- `main.py` — FastAPI app, lifespan (Redis init/close)
- `config.py` — Dynaconf settings (all env vars with `PODIUM_` prefix)
- `constants.py` — Shared types: `EventPhase`, `BAD_AUTH`, `BAD_ACCESS`, etc.
- `limiter.py` — slowapi rate limiter (user-email based)
- `db/postgres/` — SQLModel models and database session helpers
- `routers/` — API endpoints
- `validators/` — Input validation: `email.py` (disposable email), `turnstile.py` (CAPTCHA), `__init__.py` (itch.io)
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

Events are managed via:
- `backend/scripts/manage_events.py` — TUI for creating/editing events
- NocoDB — Spreadsheet UI for database (see nocodb.md)
