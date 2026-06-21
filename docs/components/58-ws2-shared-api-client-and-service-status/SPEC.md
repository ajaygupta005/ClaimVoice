# Component 58 - WS-2 Shared API Client and Service Status

## Purpose

Create the WS-2 foundation for using real backend APIs from the dashboard without each page inventing its own fetch logic, fallback behavior, or service-status display.

This component does not wire individual pages to real data yet. It creates the shared client and status contract those pages will use.

## Problem

WS-2 currently has multiple pages that can benefit from real APIs:

- Card upload can call Document AI.
- Plan details can call Eligibility.
- Provider search can call Providers.
- Voice assistant already calls Voice Agent.

The risk is that each page will handle URLs, errors, mock fallbacks, and status labels differently. That would make the UI confusing and harder to debug.

## Scope

Build a shared web API layer for:

- Voice Agent
- Eligibility
- Providers
- Document AI

Expose a common result shape:

- `ok`
- `data`
- `error`
- `statusCode`
- `source`
- `service`
- `isDemo`
- `isUnavailable`

Expose a common service status shape:

- service name
- health URL
- data mode: `real`, `demo`, `unavailable`
- latest check timestamp
- display label
- optional diagnostic message

## Required Behavior

- API client functions must avoid throwing raw network errors into UI components.
- UI components must receive typed success/error results.
- Demo fallback must be explicit in the result, not hidden.
- Service unavailable must be visible as a first-class state.
- Client code must not expose secret keys to the browser.
- Browser-facing routes must use existing Next.js API proxies where direct service access would be unsafe or brittle.

## Non-Goals

- Do not replace Card Upload mock data in this component.
- Do not replace Plan Details mock data in this component.
- Do not replace Provider Search mock data in this component.
- Do not change Voice Agent runtime behavior.
- Do not add authentication.

## Acceptance Criteria

- A shared WS-2 API client module exists.
- Service status contracts are documented in code or types.
- Voice Agent, Eligibility, Providers, and Document AI have client entry points.
- API failures produce structured UI-safe errors.
- No page silently treats mock data as real data.
- Typecheck passes.

