# Component 61 - WS-2 Provider Search from Providers APIs

## Purpose

Replace the WS-2 Providers page local mock filtering with real Providers service queries.

## Current State

The Providers page has a usable search UI, but it filters local mock data. Providers service now exposes routes that can support real search:

- `GET /api/v1/providers/search`
- `GET /api/v1/providers/{npi}`
- `GET /api/v1/providers/near`
- `POST /api/v1/providers/bulk`

## Scope

Wire Providers UI to real APIs for:

- specialty search
- location/state search
- near-me style search when coordinates are available
- accepting-new-patients filter where available
- provider detail cards
- empty/error states

## Required Behavior

- Search form submits to Providers API.
- Results render from real service data.
- Empty results are shown clearly.
- API errors do not break the page.
- Mock provider results are only used in explicit demo mode.
- Voice-agent provider answers and UI provider search should use compatible provider data.

## Data Contract

Provider cards should display:

- provider name
- NPI
- specialty
- address
- phone
- network status
- accepting new patients
- distance when available
- quality/ranking fields when available

## Non-Goals

- No provider database migrations.
- No map implementation unless reliable coordinates are already available.
- No appointment booking.
- No provider data ingestion.

## Acceptance Criteria

- Providers page fetches real search results.
- Results, empty state, loading state, and error state are implemented.
- Provider detail cards use backend data.
- Demo fallback is explicit.
- Typecheck and build pass.

