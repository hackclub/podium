# Review Checklist

Flows to verify after major changes. **Most core flows are covered by e2e tests** (see `frontend/tests/journey.spec.ts`).

## Core Flow (✅ E2E tested)
- [ ] Register for a new account
- [ ] Login using magic link
- [ ] Select an official event from the list ✅
- [ ] Create a project via the wizard ✅
- [ ] View project validation result ✅
- [ ] Edit project if validation fails ✅

## Voting (✅ E2E tested)
- [ ] Navigate to event ranking page ✅
- [ ] Vote for projects ✅
- [ ] View leaderboard ✅

## Project Management (✅ E2E tested)
- [ ] Update own project ✅
- [ ] Delete own project ✅

## Collaboration
- [ ] Join existing project via join code
- [ ] Verify collaborator appears on project

## Organizer Admin (✅ E2E tested)
- [ ] View admin panel for event ✅
- [ ] Set event phase (draft → submission → voting → closed) ✅
- [ ] View attendees list ✅
- [ ] Remove attendee ✅
