# Architecture

Podium is a peer-judging platform for Hack Club hackathons. Attendees select an official event, submit projects, and vote.

## Stack

- **Frontend:** SvelteKit (Svelte 5), Tailwind, DaisyUI
- **Backend:** FastAPI, SQLModel (async PostgreSQL)
- **Auth:** Magic link email via Loops API
- **Monitoring:** Sentry

## Data Model

Core entities:

- **User** — email, display_name, first_name
- **Event** — name, slug, feature_flags_csv, votable, leaderboard_enabled
- **Project** — name, repo, image_url, demo, owner_id, event_id, points
- **Vote** — voter_id, project_id, event_id (unique on voter+project)

M2M relationships via junction tables:
- `event_attendees` — User ↔ Event
- `project_collaborators` — User ↔ Project

## Event Series

Events are grouped into series (e.g., "scrapyard-2025"). The `ACTIVE_EVENT_SERIES` config controls which events users can select. Events with matching `feature_flags_csv` appear in the event selector.

Only one series is active at a time. Users can view past events but can only submit to the current series.

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
- `main.py` — FastAPI app
- `config.py` — Dynaconf settings
- `db/postgres/` — SQLModel models
- `routers/` — API endpoints
- `validators/` — Project validation (itch-police)

Frontend (`frontend/src/`):
- `hooks.client.ts` — Client init, auth validation
- `lib/client/` — Generated OpenAPI client
- `lib/user.svelte.ts` — User state
- `lib/validation.ts` — Project validation
- `routes/` — SvelteKit pages

## Admin Tools

Events are managed via:
- `backend/scripts/manage_events.py` — TUI for creating/editing events
- NocoDB — Spreadsheet UI for database (see nocodb.md)
