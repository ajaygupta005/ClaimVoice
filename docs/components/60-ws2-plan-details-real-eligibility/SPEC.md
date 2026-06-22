# Component 60 - WS-2 Plan Details from Eligibility APIs

## Purpose

Replace the WS-2 Plan page mock data with real member, plan, and benefit data from the Eligibility service.

## Current State

The Plan page renders a useful plan details experience, but it uses local mock data. Eligibility now exposes real read APIs that can support the page:

- `GET /api/v1/members/{member_id}/summary`
- `GET /api/v1/plans/{plan_id}/benefits`

## Scope

Wire the Plan page to:

- member summary
- plan metadata
- benefit groups
- coverage details
- cost-sharing values
- loading and error states
- explicit demo fallback

## Required Behavior

- UI loads member summary for the active member.
- UI loads benefits for the member's plan.
- UI shows real data source state.
- UI does not silently mix mock plan data with real API data.
- If Eligibility is unavailable, UI shows a recoverable error.
- Demo fallback requires an explicit demo mode.

## Data Contract

The page should display:

- member name
- member ID
- plan ID
- plan name
- plan type
- coverage status
- deductible
- out-of-pocket maximum
- common benefits
- copays/coinsurance when available
- benefit limitations when available

## Non-Goals

- No eligibility database migrations.
- No plan editing.
- No user authentication changes.
- No voice-agent behavior changes.

## Acceptance Criteria

- Plan Details page renders from Eligibility APIs.
- Loading, error, empty, and retry states exist.
- Demo fallback is visible and explicit.
- Typecheck and build pass.
- Existing mock-only plan behavior is no longer the default real path.

