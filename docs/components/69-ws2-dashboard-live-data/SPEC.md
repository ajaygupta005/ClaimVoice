# Component 69 - WS-2 Dashboard Live Data

> **Branch**: feat/live-product | **Workstream**: WS-2 | **Plan phase**: 4

## Goal

Turn the dashboard from mock fixtures into live data and smooth the browser demo path:

- Next.js proxy routes for the eligibility + providers services (mirroring the existing
  voice-agent proxy), so the browser can reach the backends.
- The Plan tab fetches the member summary + cost estimate; the Providers tab fetches
  `providers/near`. Both keep the mock fixtures as the initial value + graceful fallback so
  the page always renders.
- `/` redirects to `/dashboard/voice` (the landing page was a placeholder).
- Raise the voice respond proxy timeout so Claude compose + fact-check don't abort into the
  browser's local mock pipeline.

## Out of scope

- Card + Calls tabs (still mock-backed).
- Clerk auth enforcement (the demo runs as member `CVX-0042-MT`).
