# Flagship Event Implementation Guide

Quick reference for implementing a new flagship event (e.g., satellite-based hackathon) with custom validation.

## Quick Setup (3 Steps)

### 1. Backend - Add Feature Flag

**File:** `backend/podium/constants.py`

```python
class FeatureFlag(Enum):
    DAYDREAM = "daydream"
    SATELLITE_JAM = "satellite-jam"  # Add your event
```

### 2. Frontend - Add Event Feature (if custom validation needed)

**Directory:** `frontend/src/lib/event-features/satellite-jam/`

**`validator.ts`:**
```typescript
import type { Project } from "$lib/client/types.gen";
import type { ValidationResult } from "../types";

export function validateSatelliteProject(project: Project): ValidationResult {
  // Example: require GitHub and specific demo URL format
  const hasRepo = project.repo?.match(/github\.com\/[\w-]+\/[\w-]+/);
  const hasDemo = project.demo && project.demo.length > 0;
  
  return {
    isValid: !!hasRepo && !!hasDemo,
    message: hasRepo && hasDemo 
      ? "Project meets requirements ✅" 
      : "Need GitHub repo and demo URL",
    metadata: { prizeEligible: hasRepo && hasDemo },
  };
}
```

**`ValidationUI.svelte`:**
```svelte
<script lang="ts">
  import type { ValidationResult } from "../types";
  import type { Project } from "$lib/client/types.gen";
  
  let { validation, project } = $props();
</script>

<div class="absolute top-2 -right-4 z-20">
  <div class="bg-base-100 shadow-lg border rounded-lg p-3 text-sm">
    <div class="badge {validation.isValid ? 'badge-success' : 'badge-error'}">
      {validation.isValid ? '✓' : '✗'}
    </div>
    <span class="ml-2">{validation.message}</span>
  </div>
</div>
```

**`index.ts`:**
```typescript
import type { EventFeature } from "../types";
import { validateSatelliteProject } from "./validator";
import ValidationUI from "./ValidationUI.svelte";

export const satelliteJamFeature: EventFeature = {
  featureFlag: "satellite-jam",
  name: "Satellite Jam",
  validateProject: validateSatelliteProject,
  ValidationComponent: ValidationUI,
};

export { validateSatelliteProject };
```

**Register in `registry.ts`:**
```typescript
import { satelliteJamFeature } from "./satellite-jam";

const featuresMap = new Map<string, EventFeature>([
  [daydreamFeature.featureFlag, daydreamFeature],
  [satelliteJamFeature.featureFlag, satelliteJamFeature],
]);
```

### 3. Activate as Flagship

**File:** `frontend/src/lib/event-features/flagship-config.ts`

```typescript
export const flagshipEvents: FlagshipEventConfig[] = [
  {
    featureFlag: "daydream",
    displayName: "Daydream",
    active: false,  // Deactivate old event
  },
  {
    featureFlag: "satellite-jam",
    displayName: "Satellite Jam",
    active: true,  // Activate new event
    welcomeMessage: "Submit your satellite project for",
  },
];
```

**Create events in Airtable:**
- Set `feature_flags_csv` = "satellite-jam"

**Done!** Homepage now shows custom wizard with validation.

---

## Skip Validation (Simple Flagship)

If you don't need custom validation, skip step 2:

1. Add feature flag to backend
2. Add to flagship config with `active: true`
3. Create events in Airtable

Homepage will show wizard without validation feedback.

---

## What You Get

**Homepage:**
- Custom wizard appears when user attending flagged events
- Event pre-selected in project creation
- Fallback to StartWizard when no flagship active

**Project Creation:**
- Real-time validation feedback (if validator provided)
- Alerts show validation status as user types

**Admin Panel:**
- Validation badges on leaderboard
- Shows which projects meet requirements

---

## Edge Cases & Behavior

### Multiple Events with Same Flag Active
**Scenario:** User attending 2+ events with "satellite-jam" flag

**Behavior:**
- Wizard shows first event from the list
- User can still access other events via `/events`
- All events with the flag get validation

**Recommendation:** Use one flagship per time period (e.g., "satellite-jam-2025")

### Multiple Different Flags Active
**Scenario:** `flagship-config.ts` has 2+ events with `active: true`

**Behavior:**
- `getActiveFlagshipEvent()` returns first active event
- Only that event's wizard shown on homepage
- Other events accessible normally via `/events`

**Recommendation:** Only set one `active: true` at a time

**To support multiple simultaneous:**
```typescript
// Option 1: Use one flag, different event names
{ featureFlag: "hackathon-series", active: true }
// All events use "hackathon-series" flag

// Option 2: Switch active flag when transitioning
// Week 1: satellite-jam active
// Week 2: crypto-jam active
```

### User Not Attending Flagship Event
**Behavior:**
- Homepage shows normal `StartWizard`
- User can still attend the event via join code
- Once attending, wizard appears on next visit

### Flagship Event Exists But User Has Project
**Behavior:**
- Wizard skips to success screen
- Shows "You already have a project" message
- Links to view/edit projects and voting

### No Validation Provided
**Behavior:**
- Wizard works normally
- No real-time validation in form
- No badges in admin panel
- Project creation succeeds without checks

### Feature Flag Mismatch
**Scenario:** Event has flag "satellite-jam" but feature registered as "satellite"

**Behavior:**
- Flagship wizard shows (flag match in config)
- No validation (feature not found in registry)
- Admin panel shows no badges

**Fix:** Ensure feature flag strings match everywhere

### Event Ends, Keep Historical Data
**Deactivate flagship:**
```typescript
{ featureFlag: "satellite-jam", active: false }
```

**Keep feature in registry:**
- Admin panels still show validation for past projects
- Historical data remains valid

**Remove feature completely:**
- Delete from `flagship-config.ts`
- Delete from `registry.ts`
- Delete feature directory
- Past events no longer show validation

---

## Migration Script

Use template for bulk event creation:

```bash
cd backend
cp event_migrations/migrate_events_template.py \
   event_migrations/migrate_satellite_jam.py

# Edit constants:
SOURCE_BASE_ID = "appXXX..."
EVENT_CONFIG = {
    "feature_flag": "satellite-jam",
    "votable": False,
    "leaderboard_enabled": True,
}

# Test run
uv run python event_migrations/migrate_satellite_jam.py

# Real run (set TEST_RUN = False in script)
```

See `backend/event_migrations/README.md`

---

## File Locations

```
backend/
└── podium/constants.py              # Step 1: Add FeatureFlag

frontend/src/lib/
├── event-features/
│   ├── flagship-config.ts           # Step 3: Activate flagship
│   ├── registry.ts                  # Step 2: Register feature
│   └── satellite-jam/               # Step 2: Feature code
│       ├── index.ts
│       ├── validator.ts
│       └── ValidationUI.svelte
└── components/
    ├── FlagshipEventWizard.svelte   # Generic (don't modify)
    └── CreateProject.svelte         # Generic (don't modify)
```

---

## Testing Locally

1. Create test event in dev Airtable
2. Set `feature_flags_csv = "satellite-jam"`
3. Attend event with test user
4. Set `active: true` in flagship config
5. Visit homepage → should see wizard
6. Create project → validation feedback appears
7. Check `/events/[slug]/admin` → validation badges show

---

## Removing Old Events

**Deactivate flagship:**
```typescript
{ featureFlag: "daydream", active: false }
```

**Remove feature (optional):**
1. Delete from `flagship-config.ts` array
2. Delete from `registry.ts` map
3. Delete `frontend/src/lib/event-features/daydream/` directory
4. (Optional) Remove `DAYDREAM` from `constants.py` enum

Past events with the flag still work, just no validation/flagship treatment.

---

## Example: Daydream Implementation

See working example:
- Feature: `frontend/src/lib/event-features/daydream/`
- Validation: itch.io + GitHub URL requirements  
- Config: Entry in `flagship-config.ts` (currently `active: false`)
- Backwards compatibility: `daydreamValidation.ts` re-exports from new location
