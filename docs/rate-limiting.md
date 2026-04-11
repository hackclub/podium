# Rate Limiting

## Backend

Two mechanisms protect backend endpoints from abuse:

### Cloudflare Turnstile (unauthenticated endpoints)

Unauthenticated endpoints require a Turnstile CAPTCHA token instead of IP-based rate limiting. The token comes from the Turnstile widget on the frontend and is verified server-side via the `X-Turnstile-Token` header.

**Endpoints protected by Turnstile:**
- `POST /request-login`
- `GET /verify`
- `POST /users/` (signup)
- `GET /users/exists`

**Config:** Set `PODIUM_TURNSTILE_SECRET_KEY` in Doppler (prod) / `settings.toml` (dev). If empty, verification is skipped — no code change needed for local dev.

> ⚠️ **Production**: Never deploy without `PODIUM_TURNSTILE_SECRET_KEY` set. Unauthenticated endpoints will be completely unprotected without it.

**Implementation:** `backend/podium/validators/turnstile.py` — `require_turnstile` FastAPI dependency.

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
