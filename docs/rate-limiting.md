# Rate Limiting

## Backend

Two mechanisms protect backend endpoints from abuse:

### Cloudflare Turnstile (unauthenticated endpoints)

Unauthenticated endpoints require a Turnstile CAPTCHA token instead of IP-based rate limiting. The token comes from the Turnstile widget on the frontend and is verified server-side via the `X-Turnstile-Token` header.

**Endpoints protected by Turnstile:**
- `POST /users/` (signup)
- `GET /users/exists`

`POST /request-login` is intentionally unprotected: the signup flow reuses the same single-use token for both `POST /users/` and the immediate `POST /request-login` call, so validating twice would fail the second. The email rate limiter provides bot protection instead.

**Config:**
- **Backend:** `PODIUM_TURNSTILE_SECRET_KEY` in Doppler. If empty, server-side verification is skipped — no code change needed.
- **Frontend:** `PUBLIC_TURNSTILE_SITE_KEY` needs to be set for the widget to render and work

> ⚠️ **Production**: Both keys must be set. Without `PODIUM_TURNSTILE_SECRET_KEY` the backend accepts any request. Without `PUBLIC_TURNSTILE_SITE_KEY` the widget never renders.

**Implementation:** `backend/podium/validators/turnstile.py` — `require_turnstile` FastAPI dependency.

### Disposable email blocking

At signup and login, the email is checked against [MailChecker](https://github.com/FGRibreau/mailchecker) (55 000+ known disposable domains). Blocked emails receive a 400 error. Fails open — if MailChecker itself throws, the request proceeds rather than blocking a real user.

**Implementation:** `backend/podium/validators/email.py` — `is_disposable_email()`, called in `auth.py` and `users.py`. No config needed.

### slowapi (authenticated endpoints)

Authenticated endpoints use **user-email-based** rate limiting (extracted from the JWT). This is fairer than IP-based limits for hackathon wifi where many users share a single IP.

**Config:** `backend/podium/limiter.py` defines the limiter keyed by `get_user_email`.

**Adding a limit to a new endpoint:**

```python
from podium.limiter import limiter

@router.post("/my-endpoint")
@limiter.limit("10/minute")
async def my_endpoint(request: Request, ...):
    # request: Request is required by slowapi even if you don't use it
    ...
```

**Currently limited:** `POST /projects/validate` (10/minute per user)

## Frontend (asyncClick action)

Buttons that trigger async work use the `asyncClick` Svelte action to prevent double-clicks. It disables the button and sets `aria-busy="true"` while the handler runs.

**Usage:**

```svelte
<script>
  import { asyncClick } from "$lib/actions/asyncClick";
</script>

<button use:asyncClick={myAsyncHandler}>Submit</button>
```

**Rules:**
- Use `use:asyncClick={handler}` instead of `onclick={handler}` for any button that calls an API
- The handler must be `async` (return a Promise)
- Handlers should manage their own error display (e.g. `handleError` + toast) — the action catches exceptions only to prevent unhandled rejections
- Don't combine with manual `isLoading` state — the action replaces that pattern

## Observability

Sentry is configured with `traces_sample_rate=1.0` and a middleware (`SentryUserMiddleware` in `main.py`) that tags every request with the user's email or IP. View traces at **Explore → Traces** in Sentry.
