# Component 17 - WS-2 Dashboard Shell

> **Branch**: `feat/ws2-dashboard-shell` | **Day(s)**: 17 | **Workstream**: WS-2

## Goal

Create the main frontend shell for ClaimVoice.

This component is only the base dashboard layout. It should make the app look like one product instead of separate placeholder pages.

## Scope

Build the shared dashboard structure used by all frontend screens.

The shell should include:

- Left sidebar navigation.
- ClaimVoice brand area.
- Member context card.
- Dark mode toggle.
- Tutorial entry button.
- Main content area.
- Routes for the five dashboard tabs.

Dashboard tabs:

- Card
- Plan
- Providers
- Voice
- Calls

## Why this is first

All later WS-2 screens need the same layout. If every page builds its own layout, the UI will become inconsistent.

This component gives a common structure before adding card upload, provider search, voice chat, and call history.

## UI Requirements

The sidebar should show:

- Product name: ClaimVoice
- Short subtitle: Realtime member support
- Navigation links with icons
- Active tab styling
- Member name
- Plan name
- Member status

The main area should:

- Use a consistent page width.
- Avoid default unstyled HTML.
- Leave enough space for dashboard content.
- Work on normal laptop screen sizes.

## Routes

Create or prepare these dashboard routes:

- `/dashboard/card`
- `/dashboard/plan`
- `/dashboard/providers`
- `/dashboard/voice`
- `/dashboard/calls`

If a route is not fully implemented yet, it can show a simple placeholder inside the real dashboard shell.

## Data

Use mock member data for this component.

Example:

- Member: Maya Thompson
- Plan: Silver PPO 4500
- Status: Active

The mock data should be kept in a shared frontend mock-data file so later components can reuse it.

## Out of Scope

- Card OCR extraction.
- Provider map.
- Voice assistant behavior.
- Call playback.
- Real authentication.
- Real API integration.

Those will be handled in later WS-2 components.

## Acceptance Criteria

- Dashboard shell renders for all five routes.
- Sidebar navigation works.
- Active tab is visually clear.
- Member context is visible.
- Dark mode toggle is present.
- Tutorial button is present.
- Placeholder pages do not look like unstyled browser defaults.