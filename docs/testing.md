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

## How Auth Works

Tests create users on-the-fly via `/users/` endpoint, then get a JWT via `/verify` using a magic link token (created with `signMagicLinkToken()`). The JWT is stored in localStorage and reused for UI navigation.

## Test Structure

Journey tests follow this pattern:

1. **Setup phase (API only):**
   - Create users and authenticate
   - Create test events
   - Set up projects or other test data

2. **Testing phase (UI):**
   - Navigate pages and interact with components
   - Verify user flows work end-to-end
   - All feature testing happens through the browser

Example:

```typescript
// Setup: Create user and authenticate
const { token } = await createUserAndGetToken(email, name);
const page = await createAuthenticatedPage(browser, token, baseURL);

// Test: User joins event via EventSelector
await page.goto('/');
await page.getByText(eventName).click();
await expect(page.getByText(/joined/i)).toBeVisible();

// Test: User creates project via ProjectSubmissionWizard
await page.getByRole('button', { name: /create new project/i }).click();
// ... fill form, wait for API response ...
```

## Key Patterns

- **Authenticated pages:** Use `createAuthenticatedPage(browser, token, baseURL)` to set up localStorage with JWT
- **Wait for API calls:** Use `page.waitForResponse()` to sync with backend
- **Query selectors:** Prefer `getByRole()` for accessibility; use `getByText()` for content; avoid brittle selectors
- **Test data:** Use timestamps in names (`projectName_${Date.now()}`) to avoid collisions

## Best Practices

- **API only for infrastructure:** Limit API calls to auth, event/project setup, and test cleanup
- **Test real user flows:** All features should be tested through the UI
- **Wait for responses:** Always wait for the expected API call when testing form submissions
- **Handle flakiness:** Use reasonable timeouts (10s-15s) and `.catch(() => {})` for non-critical waits
