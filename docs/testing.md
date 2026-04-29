# Testing

E2E tests using Playwright. Tests focus on user-facing UI flows; API calls are used only for authentication and test infrastructure setup.

## Running Tests

```bash
cd frontend && doppler run --config dev -- npx playwright test

npx playwright test journey.spec.ts  # specific file
npx playwright test --ui             # UI mode
npx playwright test --headed         # see browser
```

Use `npx`, not `bunx`, for Playwright.

To run via `act` (local GitHub Actions simulation), use the helper script — it generates a short-lived Doppler service token and injects it automatically:

```bash
./scripts/run-e2e-act.sh
```

## How Auth Works

Tests create users on-the-fly via `/users/` endpoint, then get a JWT via `/verify` using a magic link token (created with `signMagicLinkToken()`). The JWT is stored in localStorage and reused for UI navigation.

## Test Files

| File | Covers |
|---|---|
| `auth.spec.ts` | Sign-up flow |
| `core.spec.ts` | Event selection, wizard visibility, leaderboard |
| `journey.spec.ts` | Full end-to-end hackathon lifecycle (organizer + attendee) |
| `wizard.spec.ts` | Project submission wizard steps |
| `admin.spec.ts` | Admin panel: phase change, attendee removal, leaderboard badges |
| `permissions.spec.ts` | Owner vs non-owner vs unauthenticated access |
| `api-coverage.spec.ts` | API contract tests (one test per endpoint) |
| `superadmin.spec.ts` | Superadmin CSV export (API-level) |

## Key Patterns

**Register `waitForResponse` before navigation** — the response may arrive before Playwright evaluates the listener if you navigate first:
```typescript
// Correct
const loaded = page.waitForResponse((r) => r.url().includes('/attendees') && r.ok());
await page.goto(`/events/${slug}`);
await loaded;

// Wrong — may miss the response
await page.goto(`/events/${slug}`);
await page.waitForResponse(...);
```

**SSR vs CSR:** SvelteKit `+page.ts` load functions run server-side on direct navigation — `waitForResponse` can't intercept them. Either assert the UI element directly (`toBeVisible`) or navigate client-side from within the app.

**Secondary users:** `createUserAndGetToken()` creates a second user via API for multi-user scenarios. Always dispose contexts in a `finally` block:
```typescript
const { authedApi: otherApi, api: otherBase } = await createUserAndGetToken(email, name);
try {
  await attendEvent(otherApi, event.id);
  // ...
} finally {
  await otherApi.dispose();
  await otherBase.dispose();
}
```

**Query selectors:** Prefer `getByRole()` for accessibility; use `getByText()` for content. Avoid `locator('.class-name')` unless scoping within a known container.

**Test data:** Use `unique('Label', testInfo)` (from `tests/utils/data.ts`) for unique names that include the worker index — avoids cross-worker collisions.
