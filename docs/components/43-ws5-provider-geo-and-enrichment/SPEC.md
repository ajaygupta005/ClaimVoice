# Component 43 - Provider Geo Search + Enrichment

> **Branch**: `feat/ws456-grounded-agent` | **Milestone**: M8 | **Workstream**: WS-5

## Goal

Add `GET /api/v1/providers/near` to the providers service (`:8003`), reproducing
the pinned `provider_lookup_eval` ranking contract EXACTLY:

1. specialty match: case-insensitive **substring** over provider specialty text
   (`taxonomy_description` or `specialty_codes`).
2. distance: **verbatim Haversine** (copied from
   `eval/tasks/provider_lookup_eval._haversine_km`) over the WKT `location`
   (`POINT(lng lat)`), kept when `distance <= radiusKm` (default 25).
3. filters: `inNetworkOnly` requires in-network for `planId`; `acceptingNewOnly`
   requires accepting-new.
4. sort: `(distanceKm asc, qualityRating desc)`.

Contract:
`GET /providers/near?specialty&lat&lng&radiusKm=25&inNetworkOnly=false&acceptingNewOnly=false&planId?&limit=50`
-> `{ total, query, providers: [ProviderNearItem] }`. `planId` is required when
`inNetworkOnly=true`.

Plus **provider enrichment**: the seeded NPPES sample carries only
`taxonomy_code` (every other field is NULL for all 500 providers). A static NUCC
crosswalk maps `taxonomy_code` -> specialty text + `specialty_codes`, and derives
deterministic `quality_rating` / `accepting_new_patients` for dev, applied via an
idempotent data backfill so `/providers/near` has specialty text + quality to
filter and rank on. The demo plan (`ClaimVoice Demo PPO`) links the nearest
providers near Midtown (40.7580, -73.9855); demo member is `CVX-0042-MT`.

## Out of scope

- PostGIS `ST_DWithin` geo (future prod optimization; dev DB has no PostGIS).
- Live Care Compare quality refresh (WS-1 owns the loaders).
- Reimplementing WS-1 loaders (`npi_ingest`, `care_compare_sync`, `mrf_parser`) —
  the service only **queries** the `providers` + `in_network` tables.
