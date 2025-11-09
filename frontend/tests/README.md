# E2E Tests

**39 tests | 100% pass rate | ~1-2 min runtime**

## Run Tests

**Stop running dev servers first:**
```bash
pkill -f podium; pkill -f "vite|bun.*dev"
```

**Run all tests:**
```bash
cd frontend
doppler run -- bun run test:e2e
```

## Commands

```bash
doppler run -- bun run test:e2e        # All tests (~1-2 min)
doppler run -- bun run test:e2e:ui     # UI mode
bunx playwright test tests/auth.spec.ts  # Specific file
```

## Performance

- **Parallel execution**: 4 workers for faster test runs
- **Server reuse**: Backend/frontend start once, shared across all workers
- **Optimized waits**: 10-30s timeouts based on operation type

## Setup

**Local:** Doppler `dev` config must have `PODIUM_JWT_SECRET` and Airtable dev credentials

**CI/CD:** Add `DOPPLER_TOKEN` to GitHub repository secrets

## Architecture

- Backend: Port 8000 (started by Playwright)
- Frontend: Port 4173 (started by Playwright)
- NOT using Vercel deployments
- Doppler injects all required env vars

**Important:** Stop any running dev servers before running tests (they will conflict on ports 8000/5173)

## Files

`auth.spec.ts` (5) | `events.organizer.spec.ts` (4) | `events.attendee.spec.ts` (6) | `projects.spec.ts` (6) | `voting.spec.ts` (4) | `admin.spec.ts` (8) | `permissions.spec.ts` (7) | `voting-integrity.spec.ts` (4) | `wizard.spec.ts` (2)
