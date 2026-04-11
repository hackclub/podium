# Theming & Event Series Setup

## Terminology

- **Event Series** — A flagship event + its satellites (e.g., "Scrapyard 2025")
- **Flagship** — Single event at one location, typically a couple weeks before satellites
- **Satellites** — Events across the world on the same weekend

All official events are treated identically in the UI — users just pick which one they're at.

## Setting Up a New Series

1. **Set `ACTIVE_EVENT_SERIES`** in Doppler (production) or `settings.toml` (local dev) to the new series slug (e.g., `apocalypse-2025`)

2. **Create events** using the manage_events TUI:
   ```bash
   cd backend && doppler run --config dev -- uv run python scripts/manage_events.py
   ```
   Set each event's `feature_flags_csv` to match the active series slug.

3. **Theme the frontend** — update branding via PR (see below)

## Theming

Each series gets custom branding — same codebase, same database, re-skinned via PR.

**What designers touch:**
- CSS/Tailwind classes, DaisyUI theme
- Component layouts and markup
- Assets (logos, images) — see `frontend/src/lib/logos/` for `CampfireFlagship` and `CampfireSat` components
- Form components in `frontend/src/lib/forms/` accept a `selectedColor` prop for per-event brand tinting
- Copy/text content

**What designers don't touch:**
- Backend code or API client generation
- Validation logic (`lib/validation.ts`)
- Auth and state management (`lib/user.svelte.ts`)

Business logic (API calls, validation, state) is separated from presentation so designers can restyle without breaking functionality.
