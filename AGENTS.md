# Commands

```bash
# Setup
cp .env.example .env                             # Create .env file with your settings

# Typecheck
pnpm --filter @podium/shared build && cd frontend && bun run svelte-check

# E2E tests (use npx, not bunx)
cd frontend && npx playwright test

# Run locally
./dev.sh                                         # Runs all services + frontend

# Database
docker compose up -d                              # Start Kafka
pnpm --filter @podium/shared db:push              # Push schema to DB (dev)
```

# Documentation

See @docs/architecture.md, @docs/database.md, @docs/testing.md, and @docs/local-dev.md.

Docs should be:
- **Concise** — fewer lines = easier to understand quickly
- **Human-skimmable** — avoid tables where prose works, don't over-format
- **Stable** — write docs that don't need frequent updates
- **Easy to edit** — plain Markdown, no complex formatting

Temporary docs (migrations, one-off playbooks) go in `docs/migrations/` and get deleted when complete.
Do not create summary documents of your actions unless the user specifically requests it.

# Quick Reference

- **Stack:** SvelteKit (Svelte 5) + NestJS microservices + PostgreSQL (Drizzle ORM)
- **Auth:** Magic link via Loops API
- **Architecture:** Gateway + 3 services (Auth, Events, Projects) + Kafka for async events
- **API client:** Regenerate with `cd frontend && bun run openapi-ts`
