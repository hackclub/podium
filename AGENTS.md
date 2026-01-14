# Commands

```bash
# Lint/typecheck (run before committing)
cd backend && uv run ruff check --fix && cd ../frontend && bun run svelte-check

# E2E tests (use npx, not bunx)
cd frontend && doppler run --config dev -- npx playwright test

# Run locally
doppler run --config dev -- uv run podium        # backend/
bun dev                                           # frontend/

# Database
docker compose up -d                              # Start Postgres + NocoDB
doppler run --config dev -- uv run alembic upgrade head  # Run migrations (backend/)
./scripts/reset-migrate.sh                        # Reset local DB
```

# Documentation

See @docs/architecture.md, @docs/database.md, @docs/testing.md, and @docs/local-dev.md.

Docs should be:
- **Concise** — fewer lines = easier to understand quickly
- **Human-skimmable** — avoid tables where prose works, don't over-format
- **Stable** — write docs that don't need frequent updates
- **Easy to edit** — plain Markdown, no complex formatting

Temporary docs (migrations, one-off playbooks) go in `docs/migrations/` and get deleted when complete.

# Quick Reference

- **Stack:** SvelteKit (Svelte 5) + FastAPI + async PostgreSQL
- **Auth:** Magic link via Loops API
- **Models:** `backend/podium/db/postgres/` (User, Event, Project, Vote, Referral)
- **API client:** Regenerate with `cd frontend && bun run openapi-ts`
