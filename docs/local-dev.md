# Local Development

## Prerequisites

- [Doppler CLI](https://docs.doppler.com/docs/install-cli) configured
- Docker (for Postgres)
- Node.js + Bun (frontend)
- Python + uv (backend)

## Quick Start

```bash
# Start Postgres
docker compose up -d

# Run migrations
cd backend && doppler run --config dev -- uv run alembic upgrade head

# Start backend
cd backend && doppler run --config dev -- uv run podium

# Start frontend (separate terminal)
cd frontend && bun dev
```

## Docker Compose

The root `docker-compose.yaml` starts Postgres on port 5432 and Redis on port 6379.

First time:
```bash
cp .env.example .env
docker compose up -d
```

Redis is optional — the app works normally without it (caching is silently disabled). To enable caching locally, set `PODIUM_REDIS_URL=redis://localhost:6379` in your Doppler dev config or `settings.toml`.

## Turnstile (CAPTCHA)

Leave `PUBLIC_TURNSTILE_SITE_KEY` unset locally — the widget won't render and the login form works normally.

To test with Turnstile active, use [Cloudflare's test keys](https://developers.cloudflare.com/turnstile/troubleshooting/testing/) (no account needed, work on localhost):

| `PUBLIC_TURNSTILE_SITE_KEY` | Behavior |
|---|---|
| `1x00000000000000000000AA` | Always passes (visible widget) |
| `2x00000000000000000000AB` | Always blocks (visible widget) |
| `3x00000000000000000000FF` | Forces interaction |

Test keys generate dummy tokens (`XXXX.DUMMY.TOKEN.XXXX`) that your real production secret will reject. Set `PODIUM_TURNSTILE_SECRET_KEY` to a matching test secret:

| `PODIUM_TURNSTILE_SECRET_KEY` | Behavior |
|---|---|
| `1x0000000000000000000000000000000AA` | Always passes |
| `2x0000000000000000000000000000000AA` | Always fails |
| `3x0000000000000000000000000000000AA` | Returns "token already spent" |

## Regenerate API Client

After backend API changes:
```bash
cd frontend && bun run openapi-ts
```

## Lint & Typecheck

```bash
cd backend && uv run ruff check --fix
cd frontend && bun run svelte-check
```
