# Component 44 - Provider Bulk Lookup

> **Branch**: `feat/ws456-grounded-agent` | **Milestone**: M9 | **Workstream**: WS-5

## Goal

Add `POST /api/v1/providers/bulk` to the providers service (`:8003`) — a batch
provider lookup by a list of NPIs.

Contract:
`POST /providers/bulk` with body `{ npis: [string] }` (1..100 NPIs) ->
`{ providers: [ProviderOut] }`. Missing NPIs are **simply omitted** from the
response (no error, no placeholder). The returned `ProviderOut` shape is identical
to the single-detail route `GET /providers/{npi}` (shared row mapper).

Like `/providers/near`, the route is registered **before** the dynamic
`/providers/{npi}` route so the static `/providers/bulk` path is not shadowed.

## Out of scope

- Pagination (the `<= 100` cap is the only bound).
- Geo / distance ranking in bulk (that is `/providers/near`).
