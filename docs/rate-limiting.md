# Rate Limiting

## Backend (slowapi)

Auth endpoints are rate-limited at **5 requests/minute per IP** using [slowapi](https://github.com/laurentS/slowapi).

**Config:** `backend/podium/limiter.py` defines the limiter and a `get_user_or_ip` key function.

**Adding to a new endpoint:**

```python
from podium.limiter import limiter  # or get_user_or_ip for per-user limits

@router.post("/my-endpoint")
@limiter.limit("10/minute")
async def my_endpoint(request: Request, ...):  # request: Request is required
    ...

# Per-user (falls back to IP for unauthenticated requests)
@router.post("/my-endpoint")
@limiter.limit("30/minute", key_func=get_user_or_ip)
async def my_endpoint(request: Request, ...):
    ...
```

**Currently limited:** `/request-login` (30/min), `/verify` (30/min)

Limits are per-IP. Set high enough for shared hackathon WiFi (many users behind one NAT) while still blocking scripted abuse.

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
- Style loading state via `button[aria-busy="true"]` if desired
- Don't combine with manual `isLoading` state — the action replaces that pattern

## Observability

Sentry is configured with `traces_sample_rate=1.0` and a middleware (`SentryUserMiddleware` in `main.py`) that tags every request with the user's email or IP. View traces at **Explore → Traces** in Sentry.
