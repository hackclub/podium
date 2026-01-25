# Official Events Only: Remove User-Created Hackathons

Refocus Podium to exclusively support official Hack Club events, removing user event creation and join codes.

## Terminology

- **Official Events** — Blanket term for all Hack Club-run hackathons (not user-created)
- **Flagship** — Single event at one location, typically a couple weeks before satellites
- **Satellites** — Events happening across the world on the same weekend
- **Event Series** — A flagship + its satellites (e.g., "Scrapyard 2025")

All official events (flagship AND satellites) are selectable by users. There's no distinction in the UI—users just pick which event they're physically at.

## Summary

Users will:
1. Sign in → select which official event they're at (flagship or any satellite) → submit a project
2. No longer create their own events or use join codes

## Key Invariants

1. **One event per user per series** — Users can only attend one official event at a time
2. **Events are pre-created** — Only admins create events; users select from existing list
3. **Active series is authoritative** — Backend validates against the active event series, not just frontend
4. **One series at a time** — Only one event series is active at any given time
5. **Shared database** — All series use the same database; users can view historical data

## Series & Theming

Each event series (e.g., "Scrapyard 2025", "Apocalypse 2025") will have:
- **Custom branding/theme** — Colors, logos, imagery, copy
- **Same codebase** — Re-skinned, not rebuilt
- **Same database** — Historical events/projects persist across series

### Designer-Friendly Customization

**Goal:** Designers/frontend devs can PR theme and layout changes without needing to understand backend or business logic.

**Approach:**
- Keep business logic (API calls, validation, state management) clearly separated from presentation
- Components should be easy to restyle without breaking functionality
- Simplify the codebase so there's less to navigate

**What designers might touch:**
- CSS/Tailwind classes, DaisyUI theme
- Component layouts and markup
- Assets (logos, images)
- Copy/text content

**What designers shouldn't need to touch:**
- Backend code
- API client generation
- Validation logic
- Authentication/state management

Users can:
- **View** past events they attended and projects they submitted
- **Not edit** projects from past series (read-only after series ends)
- **Focus on** current series for new submissions

## Scope of Changes

### Backend

#### 1. Delete Event Creation Endpoint
- **File:** `backend/podium/routers/events.py`
- **Action:** Delete `POST /events/` entirely (lines 80-111)
- **Also delete:**
  - `slugify`, `token_urlsafe` imports (if unused elsewhere)
  - `EventCreate` schema from `event.py`

#### 2. Delete Event Update/Delete Endpoints
- **File:** `backend/podium/routers/events.py`
- **Action:** Delete `PUT /events/{event_id}` and `DELETE /events/{event_id}`
- **Rationale:** Satellites are managed externally (Airtable/admin), not by users

#### 3. Replace Join Code Endpoint with Attend-by-ID
- **File:** `backend/podium/routers/events.py`
- **Action:** Delete `POST /events/attend` (join by code), replace with:
  ```python
  @router.post("/{event_id}/attend")
  async def attend_event(event_id: UUID, user, session):
      """Attend an official event by ID."""
      # Validate:
      # 1. Event exists
      # 2. Event belongs to the active series (has the active feature flag)
      # 3. User is not already attending another event in this series
      # If user already in different event: auto-switch (remove from old, add to new)
  ```
- **Critical:** Must validate event belongs to the ACTIVE series, not just any event

#### 4. Add Public Event Listing Endpoint
- **File:** `backend/podium/routers/events.py`
- **Action:** Add new endpoint:
  ```python
  @router.get("/official")
  async def list_official_events(session) -> list[EventPublic]:
      """List all official events for the current series (flagship + satellites)."""
      # Query events where feature_flags_csv contains active series flag
      # No auth required - public list
  ```
- **Note:** Active series flag must be defined server-side (config or env var), not just in frontend

#### 5. Simplify UserEvents Response
- **File:** `backend/podium/routers/events.py`
- **Action:** Simplify `GET /events/` to only return `attending_events`
- **Delete:** `owned_events` field from `UserEvents` response

#### 6. Remove join_code from EventPrivate Schema
- **File:** `backend/podium/db/postgres/event.py`
- **Action:** Remove `join_code` from `EventPrivate` (keep in DB table for historical reference)

#### 7. Delete Slug Lookup Endpoint (Optional)
- **File:** `backend/podium/routers/events.py`
- **Action:** Consider deleting `GET /events/id/{slug}` if not needed

---

### Backend: Remove Review Factory, Add Itch-Police Validator

#### 8. Delete Review Factory Integration
- **Files to delete:**
  - `backend/podium/generated/review_factory_models.py`
  - `backend/regenerate_models.py` (Review Factory model generator)
- **File:** `backend/podium/routers/projects.py`
  - Delete `POST /check/start` endpoint (lines 199-234)
  - Delete `GET /check/{check_id}` endpoint (lines 237-255)
  - Remove `httpx` import if unused elsewhere
- **File:** `backend/podium/config.py`
  - Delete `review_factory_url` and `review_factory_token` validators (lines 72-79)
- **File:** `backend/settings.toml`
  - Delete `review_factory_url` setting
- **File:** `docs/architecture.md`
  - Remove Review Factory from external integrations

#### 9. Add Itch-Police Validator Endpoint
- **File:** `backend/podium/routers/projects.py`
- **New endpoint:**
  ```python
  @router.post("/validate")
  async def validate_project(project_id: UUID, session) -> ValidationResult:
      """Validate a project's demo URL (itch.io playability check)."""
      # 1. Fetch project from DB
      # 2. Check demo URL is itch.io format
      # 3. HTTP GET the itch.io page
      # 4. Parse HTML, look for .game_frame element
      # 5. Return { valid: bool, message: str }
  ```
- **Logic from itch-police:**
  ```python
  def is_playable(url: str) -> bool:
      response = requests.get(url, timeout=10)
      soup = BeautifulSoup(response.content, 'html.parser')
      game_frames = soup.select('.game_frame')
      return len(game_frames) > 0
  ```
- **Dependencies:** Add `beautifulsoup4` to backend requirements

#### 10. Create Validation Models
- **File:** `backend/podium/db/postgres/validation.py` (new)
  ```python
  class ValidationResult(BaseModel):
      valid: bool
      message: str
      
  class ValidationStatus(BaseModel):
      status: Literal["valid", "invalid", "error"]
      message: str
      checked_at: datetime
  ```

---

### Frontend

#### 11. Delete Event Creation UI
- **Delete files:**
  - `frontend/src/routes/events/create/+page.svelte`
  - `frontend/src/lib/components/CreateEvent.svelte`
- **File:** `frontend/src/routes/+layout.svelte`
- **Action:** Remove "Create Event" from sidebar dropdown (lines 279-305)
- **Simplify:** Remove events dropdown complexity entirely; just link to `/events`

#### 12. Delete Join Code / Attend Event UI
- **Delete files:**
  - `frontend/src/lib/components/AttendEvent.svelte`
  - `frontend/src/routes/events/attend/` (entire directory if exists)

#### 13. New Component: EventSelector
- **File:** `frontend/src/lib/components/EventSelector.svelte`
- **Purpose:** Let users search/select from all official events (flagship + satellites)
- **Features:**
  - Fetch events from new `/events/official` endpoint
  - Searchable list (filter by name as user types)
  - Click to join (calls new `/events/{event_id}/attend`)
  - Show event name + description
  - Call `customInvalidateAll()` after joining to refresh homepage state

#### 14. Rewrite Homepage Flow
- **File:** `frontend/src/routes/+page.svelte`
- **Current:** Complex logic checking flagship events vs StartWizard
- **New simplified flow:**
  ```
  if (no active series configured) → Show "No active event" message
  else if (user NOT attending any event) → Show EventSelector
  else if (user has NO project for their event) → Show project submission wizard
  else → Show success screen (view/edit projects, voting links)
  ```
- **Delete:** All `StartWizard` references

#### 15. Delete StartWizard
- **Delete file:** `frontend/src/lib/components/StartWizard.svelte`
- **Rationale:** Replaced by EventSelector + project submission wizard

#### 16. Simplify/Rename FlagshipEventWizard → ProjectSubmissionWizard
- **File:** `frontend/src/lib/components/FlagshipEventWizard.svelte`
- **Rename to:** `ProjectSubmissionWizard.svelte`
- **Simplify validation:** Remove event-feature system complexity, use single validator
- **Keep:** Create/Join project flow, validation UI, success screen, edit on failure

#### 17. Remove Join Code from Admin Panel
- **File:** `frontend/src/lib/components/event-admin/AdminPanel.svelte`
- **Action:** Delete "Event Join Code" card entirely (lines 156-206)
- **Keep:** Event settings, attendees table, leaderboard

#### 18. Simplify Events Page
- **File:** `frontend/src/routes/events/+page.svelte`
- **Action:**
  - Remove "Attend an Event" link (line 55)
  - Remove "Events You Own" section entirely (lines 61-112)
  - Remove join_code column references
- **New structure:**
  - **Current Series:** Show user's current event (if attending) with prominent link
  - **Past Events:** Show read-only list of past events user attended (collapsed/secondary)

#### 19. Delete Event Admin Update UI
- **File:** `frontend/src/lib/components/event-admin/UpdateEvent.svelte`
- **Action:** Delete (events managed externally, not by users)

#### 20. Delete Entire Event-Features System
- **Delete entire directory:** `frontend/src/lib/event-features/`
  - `daydream/` (validator.ts, ValidationUI.svelte, index.ts)
  - `registry.ts`
  - `types.ts`
  - `flagship-config.ts`
- **Rationale:** No per-event validators needed; single validation for all official events

#### 21. Create Simple Unified Validation Module
- **New file:** `frontend/src/lib/validation.ts`
  ```typescript
  // Simple regex checks (client-side, instant feedback)
  export function isValidItchUrl(url: string): boolean { ... }
  export function isValidGitHubUrl(url: string): boolean { ... }
  
  // Backend validation (itch-police playability check)
  export async function validateProject(projectId: string): Promise<{
    valid: boolean;
    message: string;
  }> {
    // Call POST /projects/validate
  }
  ```
- **Replaces:** All of event-features + async.ts complexity

#### 22. Simplify async.ts
- **File:** `frontend/src/lib/async.ts`
- **Delete:**
  - `pollForCompletion()` function
  - `checkProjectQuality()` function
  - All imports from event-features
- **Replace with:** Import from new `validation.ts` module
- **Or:** Delete `async.ts` entirely if only used for validation

#### 23. Simplify ProjectSubmissionWizard (formerly FlagshipEventWizard)
- **File:** `frontend/src/lib/components/FlagshipEventWizard.svelte` → rename to `ProjectSubmissionWizard.svelte`
- **Remove:**
  - `getEventFeature()` calls and all feature-flag branching
  - `eventFeature` derived state
  - `lastValidatedProject` hash and `$effect` auto-revalidate loop
- **Simplify to:**
  ```typescript
  // Always validate after project create/join
  async function handleProjectCreated() {
    currentStep = "validating";
    const result = await validateProject(project.id);
    validationResult = result;
    currentStep = result.valid ? "success" : "failure";
  }
  
  // Re-validate after edit
  async function handleProjectUpdated() {
    await handleProjectCreated(); // same flow
  }
  ```
- **Keep:** Same UI steps (chooseProject → create/join → validating → success/failure)

#### 24. Simplify Homepage (+page.svelte)
- **File:** `frontend/src/routes/+page.svelte`
- **Remove:**
  - `getActiveFlagshipEvent()` import and usage
  - `isFlagshipEvent()` import and usage
  - Feature flag filtering logic
- **Simplify to:**
  ```typescript
  // Fetch user's attending events
  // If attending any event → show ProjectSubmissionWizard
  // If not attending any → show EventSelector
  // No feature flag checks needed
  ```

#### 25. Simplify ProjectCardWrapper
- **File:** `frontend/src/lib/components/ProjectCardWrapper.svelte`
- **Remove:** Review Factory modal and complex validation UI
- **Simplify to:** Just show valid/invalid badge based on project status

#### 26. Regenerate API Client
- **Command:** `cd frontend && bun run openapi-ts`
- **When:** After all backend endpoint changes
- **Rationale:** Remove dead types, add new endpoint types

---

### Data & Configuration

#### 27. No Database Migration Needed
- `join_code` field stays in DB (historical data)
- `cached_auto_quality` field can be removed (was for Review Factory caching)
- No schema changes required

#### 28. Backend Series Configuration
- **File:** `backend/podium/config.py`
- **Action:** Add active series flag as server-side config (env var or settings)
- **Example:** `ACTIVE_EVENT_SERIES = "scrapyard-2025"`
- **Rationale:** Backend must validate attend requests, not trust frontend
- **Also:** Remove `review_factory_url` and `review_factory_token` from config

#### 29. Official Event Setup (Admin)
- All official events (flagship + satellites) pre-created in database with correct `feature_flags_csv`
- Active series set in backend config only (no frontend config needed anymore)

#### 30. Ensure Clean Separation for Designer PRs
- **Goal:** Designers can modify layouts/styles without breaking business logic
- **Action:** During simplification, ensure:
  - API calls are in dedicated files (not inline in components)
  - Validation logic is in `validation.ts` (not scattered)
  - State management is clear and isolated
- **Result:** Fewer files, cleaner components, easier for designers to navigate

#### 31. Projects Page: Current vs Historical
- **File:** `frontend/src/routes/projects/+page.svelte`
- **Current series projects:** Editable (if series is active)
- **Past series projects:** Read-only view
- **Backend:** Add `is_active_series` flag to project responses, or derive from event's feature flag

---

## New User Flow

```
1. User signs in
   │
   ├─── No active series configured ─────────┐
   │                                         ▼
   │                              "No active hackathon"
   │                              [Sign Out]
   │
   ├─── Not attending any event ─────────────┐
   │                                         ▼
   │                              EventSelector
   │                              "Which event are you at?"
   │                              [Searchable list of flagship + all satellites]
   │                              [Can switch events later]
   │                                         │
   │    ┌────────────────────────────────────┘
   ▼    ▼
2. User is in an event
   │
   ├─── No project for this event ───────────┐
   │                                         ▼
   │                              ProjectSubmissionWizard
   │                              [Create New Project]
   │                              [Join Existing Project]
   │                                         │
   │    ┌────────────────────────────────────┘
   ▼    ▼
3. User has a project ───────────────────────┐
                                             ▼
                                  SuccessScreen
                                  [View/Edit Projects]
                                  [Voting/Galleries]
                                  [Change Event] (optional)
                                  [Sign Out]
```

---

## Files to Delete

### Frontend
- `frontend/src/routes/events/create/+page.svelte`
- `frontend/src/routes/events/create/` (directory)
- `frontend/src/routes/events/attend/` (directory if exists)
- `frontend/src/lib/components/CreateEvent.svelte`
- `frontend/src/lib/components/AttendEvent.svelte`
- `frontend/src/lib/components/StartWizard.svelte`
- `frontend/src/lib/components/event-admin/UpdateEvent.svelte`
- `frontend/src/lib/event-features/` (entire directory)

### Backend
- `backend/podium/generated/review_factory_models.py`
- `backend/regenerate_models.py`

### Backend (code to delete from files)
- `POST /events/` endpoint
- `POST /events/attend` endpoint (join by code)
- `PUT /events/{event_id}` endpoint
- `DELETE /events/{event_id}` endpoint
- `POST /check/start` endpoint (Review Factory)
- `GET /check/{check_id}` endpoint (Review Factory)
- `EventCreate` schema
- `review_factory_url` and `review_factory_token` config

---

## Files to Create

- `frontend/src/lib/components/EventSelector.svelte` — select official event UI
- `frontend/src/lib/validation.ts` — unified project validation (replaces event-features)
- `backend/podium/validators/itch_police.py` — itch.io playability checker

---

## Implementation Order

### Phase 1: Backend - Events
1. Add `ACTIVE_EVENT_SERIES` to backend config
2. Add `GET /events/official` endpoint (public, no auth) — lists all events in active series
3. Add `POST /events/{event_id}/attend` endpoint with validation:
   - Event must belong to active series
   - Auto-switch if user already in different event
4. Delete old endpoints: create, attend (join code), update, delete
5. Simplify `GET /events/` response (remove owned_events)
6. Remove `join_code` from `EventPrivate` schema

### Phase 2: Backend - Validation
1. Delete Review Factory integration:
   - Delete `POST /check/start` and `GET /check/{check_id}` endpoints
   - Delete `review_factory_models.py` and `regenerate_models.py`
   - Remove config: `review_factory_url`, `review_factory_token`
2. Add itch-police validator:
   - Create `backend/podium/validators/itch_police.py`
   - Add `POST /projects/validate` endpoint
   - Add `beautifulsoup4` to dependencies

### Phase 3: Frontend - New Components
1. Create `EventSelector.svelte` (select official event)
2. Create `validation.ts` (unified validation module)
3. Rewrite `+page.svelte` homepage with new simplified flow
4. Regenerate API client: `bun run openapi-ts`

### Phase 4: Frontend - Delete & Simplify
1. Delete `frontend/src/lib/event-features/` (entire directory)
2. Delete files: CreateEvent, AttendEvent, StartWizard, UpdateEvent
3. Delete routes: `/events/create`, `/events/attend`
4. Delete or simplify `async.ts` (remove Review Factory polling)
5. Simplify sidebar in `+layout.svelte` (remove Create Event)
6. Remove join code card from AdminPanel
7. Simplify `/events` page (remove owned events, join code columns)
8. Rename FlagshipEventWizard → ProjectSubmissionWizard and simplify:
   - Remove all feature-flag branching
   - Remove `getEventFeature()` calls
   - Use new `validation.ts` module
9. Simplify ProjectCardWrapper (remove Review Factory modal)

### Phase 5: Test ✅ COMPLETE
1. New user → select event (flagship or satellite) → submit project → success
2. Project validation → itch.io game is browser-playable → success
3. Project validation fails → user can edit and resubmit
4. User switches event → old attendance removed, new added
5. User with project → sees success screen
6. No active series → sees "no event" message
7. Voting still works

**E2E Tests Updated:**
- All 13 tests pass
- Added `POST /events/test/create` endpoint for test event creation
- Updated test helpers: `createTestEvent()`, `getOfficialEvents()`, `attendEvent()`
- Rewrote test files for new official-events-only flow

---

## Backward Compatibility

### Old Join Links (`?join_code=...`)
- **Option A (recommended):** Keep `/events/attend` route as redirect to homepage with toast message
- **Option B:** Return 404, let old links break
- **Decision:** TBD based on how many links are in the wild

---

## Decisions Made

1. ✅ **Delete event creation** — Users cannot create events
2. ✅ **Delete event update/delete** — Events managed externally (DB/Airtable)
3. ✅ **One event per user per series** — Backend enforces; auto-switch on re-select
4. ✅ **Keep project join codes** — Collaborators can still join projects via code
5. ✅ **No referral tracking on event select** — Simplify flow (can add back later if needed)
6. ✅ **Flagship and satellites treated identically** — All are "official events" in one list
7. ✅ **Remove Review Factory** — Replace with itch-police validator
8. ✅ **Single validation system** — Same checks for all events (no per-event validators)

---

## Out of Scope (Future)

- Admin UI for creating/managing events (use direct DB or NocoDB)
- Multiple simultaneous event series
- Location/region fields on events (just use name + description for now)
- Distinguishing flagship from satellites in UI (they're all just "events")
- Complex validation (README analysis, image checks) — just itch.io playability for now
- Dynamic theming from backend (theming is file-based, changed per series via PR)
