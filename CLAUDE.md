# Podium — Claude Code Guidelines

Podium is a peer-judging platform for Hack Club hackathons. Attendees select an official event, submit projects, and vote on each other's work.

## Architecture

### System Overview

```
                    Gateway (Node.js, port 3000)
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
  Auth Service       Events Service     Projects Service
  (NestJS, 8001)    (NestJS, 8002)      (NestJS, 8003)
        │                  │                  │
        └──────────────────┴──────────────────┘
                           │
                     PostgreSQL + Kafka
```

The gateway (`gateway/`) is a simple HTTP reverse proxy. All `/api/auth/*` and `/api/users/*` go to auth-service, `/api/events/*` to events-service, `/api/projects/*` to projects-service. Everything else proxies to the SvelteKit frontend.

### Monorepo Layout (pnpm workspaces)

```
podium/
├── gateway/                    # HTTP proxy (Node.js)
├── packages/
│   ├── shared/                 # DB schema, auth guards, Drizzle config
│   ├── auth-service/           # Magic link auth, JWT, admin OTP
│   ├── events-service/         # Events, voting (→ Kafka), leaderboard
│   └── projects-service/       # Projects, screenshot upload (R2/S3)
├── frontend/                   # SvelteKit 2 + Svelte 5
└── docs/                       # Architecture, setup, testing docs
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | SvelteKit 2, Svelte 5 (runes), Tailwind CSS 4, DaisyUI 5 |
| Backend | NestJS 11, TypeScript 5 |
| Database | PostgreSQL, Drizzle ORM |
| Queue | Kafka (`votes` topic) |
| Auth | JWT + magic link (Loops API) |
| File Storage | Cloudflare R2 / AWS S3 |
| Monitoring | Sentry |
| Package Manager | pnpm |
| Testing | Playwright (E2E) |

### Database Schema

Defined in `packages/shared/src/db/schema.ts` using Drizzle ORM. Core tables:

- **users** — `id` (uuid PK), `email` (unique), `display_name`, `is_admin`
- **events** — `id`, `slug` (unique), `enabled`, `votable`, `leaderboard_enabled`, `feature_flags_csv`, theme fields
- **projects** — `id`, `name`, `repo`, `demo`, `join_code` (unique), `owner_id` → users, `event_id` → events
- **votes** — `voter_id` → users, `project_id` → projects, `event_id` → events; UNIQUE on `(voter_id, project_id)`
- **event_attendees** — junction, UNIQUE on `(event_id, user_id)`
- **project_collaborators** — junction, UNIQUE on `(project_id, user_id)`

DB migrations: `pnpm --filter @podium/shared db:push` (dev) or `db:migrate` (prod).

### Database Connection Routing

Three injection tokens are available from `@podium/shared`. Always use the correct one:

| Token | Endpoint | Use for |
|-------|----------|---------|
| `DRIZZLE_RW` | `postgresql-cluster-rw` | All writes (INSERT, UPDATE, DELETE) **and** reads that directly guard a write (e.g. "does this slug exist?" before insert, pre-write ownership checks) |
| `DRIZZLE_RO` | `postgresql-cluster-ro` | General reads that are user-facing but not guarding an imminent write (e.g. fetching a user by ID for auth, listing attended events, admin data views) |
| `DRIZZLE_R` | `postgresql-cluster-r` | Eventually-consistent reads where slight lag is acceptable (leaderboard, public event/project listings, vote counts) |

Rules of thumb:
- If the read result will be used to decide whether to perform a write **in the same request**, use `DRIZZLE_RW`.
- If it's a standalone read and stale-by-milliseconds is fine, use `DRIZZLE_RO` or `DRIZZLE_R`.
- The legacy `DRIZZLE` token still exists as an alias to `DRIZZLE_RW` for backwards compatibility — do not use it in new code.

Inject all three in the constructor only if the service actually uses all three; omit unused tokens.

### Voting Pipeline

Votes are high-throughput. The flow is:

1. Frontend `POST /api/events/vote` — sends ballot to events-service
2. Events-service publishes to Kafka topic `votes`
3. Events-service Kafka consumer aggregates vote counts in PostgreSQL
4. Leaderboard reads aggregated counts

This decouples write throughput from DB writes. The Kafka `votes` topic is the source of truth for raw vote intent.

### Authentication

- **Users:** magic link via Loops API → JWT stored in localStorage
- **Admins:** OTP via email → JWT with `is_admin: true`
- **Guards:** `JwtAuthGuard` and `AdminGuard` from `@podium/shared/auth`
- **Decorator:** `@CurrentUser()` injects authenticated user into handlers

### Frontend Routing

```
/                        — Event selector
/[slug]                  — Event landing (layout loads event + theme)
/[slug]/create           — Submit/edit project
/[slug]/vote             — Voting interface
/[slug]/vote/[id]        — Project detail
/admin/login             — Admin OTP login
/admin/events/[id]/...   — Event management (attendees, leaderboard, projects, theme)
```

Key frontend files:
- `frontend/src/lib/api.ts` — Typed REST client for all API calls
- `frontend/src/lib/auth.ts` — Token storage/retrieval
- `frontend/src/lib/theme.ts` — Per-event theming (colors, font, logo)
- `frontend/src/lib/forms/` — Reusable form components

## Performance Requirements

**This app must handle 10,000 requests/second for project creation and voting.**

- **Never introduce synchronous blocking** in the hot paths (`POST /events/vote`, `POST /projects`). Vote writes go through Kafka — keep it that way. Do not bypass the queue.
- **Avoid N+1 queries.** Use Drizzle joins or batched queries. Never query inside a loop.
- **Parallelize independent DB reads.** Use `Promise.all` for lookups that don't depend on each other. Example: `createProject` fetches event and attendee row in parallel.
- **Never use a pre-insert DB lookup loop to generate unique codes.** Generate random codes with enough entropy that collisions are negligible (currently 5 bytes → ~1T combinations for join codes), then rely on the DB UNIQUE constraint + a small retry loop (max 3 attempts) on `code=23505` conflict. This eliminates serial round-trips.
- **Keep hot-path handlers thin.** Business logic that doesn't need to block the response should be offloaded (Kafka, background jobs).
- **Connection pooling is assumed.** Do not open new DB connections per request.
- **Frontend performance:** Parallelize independent API calls with `Promise.all`. Prefer server-side rendering or static generation where possible. Avoid client-side waterfalls. Keep bundle size small — no heavy deps unless justified.
- **Do not add polling loops or setTimeout-based retries** in any service. If retry logic is needed, use Kafka's built-in retry mechanisms.

## Data Integrity

**Data integrity is the top priority. Never sacrifice correctness for speed.**

- **Votes are sacred.** The `UNIQUE(voter_id, project_id)` constraint in PostgreSQL is the final guard against duplicate votes. Never remove it. Never skip it. Kafka deduplication is a first pass — the DB constraint is the authoritative last line.
- **All writes that must be atomic must use transactions.** Drizzle supports `db.transaction()`. Use it for any multi-step write where partial success would be incorrect (e.g., creating a project + adding the owner as attendee).
- **Foreign key constraints must be preserved.** Do not delete referenced rows without cascading or checking dependents.
- **Do not silently swallow errors.** If a write fails, propagate the error. Returning 200 on a failed write is a data integrity bug.
- **Validate at the boundary.** Input validation happens in NestJS DTOs (class-validator). Do not rely on the DB to be the first validator for business rules — reject bad data early.
- **Event attendee enforcement:** A user may only attend one event per series. This is enforced in events-service. Any change to attendee logic must preserve this invariant.
- **Vote eligibility:** Users cannot vote for projects they own or collaborated on. This check must happen server-side, never trust the client.

## Styling Guidelines

The frontend uses **Tailwind CSS 4** and **DaisyUI 5**. Follow these conventions:

- **Use DaisyUI component classes first** (`btn`, `input`, `card`, `modal`, etc.) before reaching for raw Tailwind utilities. DaisyUI handles theming tokens automatically.
- **No custom CSS files.** All styles go in class attributes. No `<style>` blocks unless absolutely necessary for dynamic/animation behavior that Tailwind cannot express.
- **Theming is data-driven.** Each event has a theme stored in the DB (`theme_name`, `theme_background`, `theme_font`, `theme_primary`, `theme_selected`). The `eventToTheme()` function in `lib/theme.ts` merges these with defaults. Apply theme values via CSS variables or inline styles — do not hardcode event colors.
- **Svelte 5 runes** (`$state`, `$derived`, `$effect`, `$props`) are the only state primitives. Do not use Svelte 4 `$:` reactive statements or `writable()` stores for new code.
- **No UI framework beyond DaisyUI** (no shadcn, no flowbite, no headlessui). Keep the dep tree lean.
- **Accessible markup.** Use semantic HTML. Buttons must be `<button>`, not `<div onclick>`. Form inputs get labels.
- **Toast notifications** use `svelte-sonner`. Import `toast` from it, not `alert()`.

## Common Commands

```bash
# Dev (all services + frontend)
pnpm run dev

# Database
pnpm --filter @podium/shared db:push       # Push schema (dev)
pnpm --filter @podium/shared db:migrate    # Run migrations (prod)
pnpm --filter @podium/shared db:studio     # Drizzle visual studio

# Build shared types (required before frontend type-check)
pnpm --filter @podium/shared build

# Regenerate frontend API client from OpenAPI spec
cd frontend && bun run openapi-ts

# Frontend type check
cd frontend && bun run svelte-check

# E2E tests
cd frontend && npx playwright test
```

## Key Invariants (Do Not Break)

1. `UNIQUE(voter_id, project_id)` on `votes` table — enforces one vote per user per project
2. `UNIQUE(event_id, user_id)` on `event_attendees` — one event per user per series
3. `UNIQUE(project_id, user_id)` on `project_collaborators` — no duplicate collaborators
4. Votes go through Kafka before being persisted — do not write votes directly to DB from the HTTP handler
5. JWT secret (`PODIUM_JWT_SECRET`) must never be logged or exposed in responses
6. Admin routes require `AdminGuard` — never expose admin endpoints without it
