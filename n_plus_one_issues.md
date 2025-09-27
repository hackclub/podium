# N+1 Query Issues & Lookup Field Opportunities

## High Impact
- **Vote table**: Add `voter_display_name` and `project_name` lookup fields to eliminate user/project lookups in admin panels
  - Used in: `frontend/src/lib/components/event-admin/AdminPanel.svelte`
- **Event table**: Add `owner_display_name` lookup field to eliminate user lookups when displaying event lists
  - Used in: `frontend/src/routes/events/+page.svelte`, `frontend/src/routes/projects/+page.svelte`
- **Referral table**: Add `user_display_name` and `event_name` lookup fields to eliminate user/event lookups in admin panels
  - Used in: `frontend/src/lib/components/event-admin/AdminPanel.svelte`

## Medium Impact  
- **Project table**: Add `event_name` lookup field to eliminate event lookups when displaying projects
  - Used in: `frontend/src/routes/projects/+page.svelte`, `frontend/src/lib/components/ProjectCardWrapper.svelte`
- **User table**: Add `attending_event_names` and `owned_event_names` lookup fields to eliminate event lookups in user event lists
  - Used in: `frontend/src/routes/events/+layout.ts`, `frontend/src/routes/+layout.svelte`
- **Vote table**: Add `event_name` lookup field for better context in vote displays
  - Used in: `frontend/src/lib/components/event-admin/AdminPanel.svelte`

## Already Fixed
- **Project table**: `collaborator_display_names` and `owner_display_name` lookup fields (eliminates N+1 in ProjectCard components)
  - Fixed in: `frontend/src/lib/components/ProjectCard.svelte`

## Current N+1 Patterns
- Admin panel manually builds lookup maps from attendees/projects
- Event lists require individual owner lookups
- Vote displays require individual voter lookups
- Referral displays require individual user lookups
