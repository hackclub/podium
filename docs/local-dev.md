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
