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

The root `docker-compose.yaml` starts Postgres on port 5432 and optionally NocoDB on port 8080.

First time:
```bash
cp .env.example .env
docker compose up -d
```

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
