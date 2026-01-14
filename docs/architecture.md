# Architecture

Podium is a peer-judging platform for hackathons. Attendees submit projects, explore submissions, and vote. Organizers manage events, attendance, and leaderboards.

## Stack

- **Frontend:** SvelteKit (Svelte 5), Tailwind, DaisyUI
- **Backend:** FastAPI, SQLModel (async PostgreSQL)
- **Auth:** Magic link email via Loops API
- **Monitoring:** Sentry
- **External:** Review Factory (project quality checks)

## Data Model

Core entities:

- **User** — email, display_name, first_name
- **Event** — name, slug, join_code, owner_id, votable, leaderboard_enabled
- **Project** — name, repo, image_url, demo, owner_id, event_id, points
- **Vote** — voter_id, project_id, event_id (unique on voter+project)
- **Referral** — content, user_id, event_id

M2M relationships via junction tables:
- `event_attendees` — User ↔ Event
- `project_collaborators` — User ↔ Project

## Voting Rules

Vote limits scale with project count: 1 vote (< 4 projects), 2 votes (4-19), 3 votes (≥ 20). Users can't vote for their own or collaborated projects.

## Key Directories

Backend (`backend/podium/`):
- `main.py` — FastAPI app
- `config.py` — Dynaconf settings
- `db/postgres/` — SQLModel models
- `routers/` — API endpoints

Frontend (`frontend/src/`):
- `hooks.client.ts` — Client init, auth validation
- `lib/client/` — Generated OpenAPI client
- `lib/user.svelte.ts` — User state
- `routes/` — SvelteKit pages
