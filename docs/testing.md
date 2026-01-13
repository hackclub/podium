# Testing

E2E tests using Playwright with worker-scoped authentication.

## Running Tests

```bash
cd frontend && doppler run --config dev -- npx playwright test

npx playwright test core.spec.ts  # specific file
npx playwright test --ui          # UI mode
npx playwright test --headed      # see browser
```

Use `npx`, not `bunx`, for Playwright.

## How Auth Works

Each Playwright worker gets a unique test user (`test+pw{workerIndex}@example.com`). JWT is obtained via the `/verify` endpoint and stored in localStorage. The token is reused across all tests in that worker.

## Writing Tests

```typescript
import { test, expect } from './fixtures/auth';
import { unique } from './utils/data';

test('example', async ({ authedPage, api }, testInfo) => {
  const name = unique('Event', testInfo);  // collision-free names
  // authedPage is pre-authenticated
  // api is APIRequestContext for backend calls
});
```

Key utilities:
- `fixtures/auth.ts` — `test`, `authedPage`, `api` fixtures
- `utils/waiters.ts` — `waitForApiOk()`, `clickAndWaitForApi()`
- `utils/data.ts` — `unique(name, testInfo)`
- `helpers/api.ts` — `createEvent()`, `createProject()`, etc.

## Best Practices

- Use `unique()` for entity names to avoid collisions
- Wait for API responses with `clickAndWaitForApi()` or `waitForResponse()`
- Prefer `getByRole()` or `data-testid` over text selectors
- Add `.first()` for ambiguous selectors
