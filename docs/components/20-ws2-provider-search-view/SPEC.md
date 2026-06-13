# Component 20 - WS-2 Provider Search View

> **Branch**: `feat/ws2-provider-search-view` | **Day(s)**: 20 | **Workstream**: WS-2 / WS-5 integration surface

## Goal

Replace the Providers tab placeholder with a frontend provider search screen.

This is a frontend-only component. Real PostGIS/provider backend integration is not required yet. Use mock/demo provider data, but align the UI with the WS-5 provider directory work.

## Source Data

Use these repo files as reference:

- `docs/PROJECT_DEEPDIVE.md`
- `data/SPEC.md`
- `services/providers/README.md`
- `apps/web/src/components/ProviderMap.tsx`

## Scope

Build the Providers tab at:

- `/dashboard/providers`

The screen should show:

- Search/filter controls
- Provider result cards
- Mock map/location panel
- Selected provider details

## Out of Scope

- Real NPI lookup.
- Real PostGIS query.
- Real MRF in-network filtering.
- Real Care Compare API.
- Real appointment scheduling.
- Backend changes.

## Acceptance Criteria

- Providers tab no longer shows a placeholder.
- Provider filters are visible.
- Mock provider results are shown.
- User can select a provider.
- Selected provider details are visible.
- Mock map panel is clearly labelled as demo data.
- UI matches the dashboard shell and existing card/plan styling.