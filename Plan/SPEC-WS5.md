# SPEC — WS-5 Provider Directory & Geo

> Service: `services/providers` (FastAPI, port 8003). Milestones M8–M9.
> Delivers the `find_provider` capability the voice agent calls: geo + specialty + in-network +
> accepting-new ranking. **Geo is app-side Haversine** (works on plain Postgres; PostGIS is a future opt).

**Status: ✅ implemented & tested (M8–M9) — see `Plan/HANDOFF.md`.** The sections below describe
the original plan/baseline.

## Current state (baseline)

- 2 real endpoints: `/api/v1/providers/search`, `/api/v1/providers/{npi}` via
  `repositories/provider_repo.py` (`_SELECT_COLS`, `_row_to_provider`, `search_providers`,
  `get_provider_by_npi`). `planId` param is a documented **no-op**.
- All `services/*.py` are stubs (geo_search, in_network, care_compare, quality_enrichment, npi_loader).
- **Provider enrichment is empty:** `quality_rating`, `accepting_new_patients`, `taxonomy_description`,
  `specialty_codes`, `hospital_name` are NULL for all 500 seeded providers; only `taxonomy_code` (NUCC) exists.
- `in_network` links only 10 distinct NPIs across 16 plans.

## Contract is PINNED by the eval — do not change its semantics

`eval/tasks/provider_lookup_eval.py` defines the reference `rank_providers(query, candidates)` +
`_haversine_km` + `score_case`, with 7 golden cases in `eval/datasets/provider_queries.json` and
`eval/tests/test_provider_lookup.py`. The live `/providers/near` endpoint **must reproduce
`rank_providers` exactly**:
- specialty: case-insensitive **substring** match on provider specialty text
- distance: **verbatim `_haversine_km`** (copy it into `services/geo_search.py`) over the WKT
  `location` (`POINT(lng lat)`); keep if `distance ≤ radiusKm` (default 25)
- filters: `inNetworkOnly` requires in-network; `acceptingNewOnly` requires accepting-new
- sort: `(distanceKm asc, qualityRating desc)`

Do **not** edit the eval files; treat them as the contract test.

## Deliverables & milestones

### M8 — enrich providers + `GET /api/v1/providers/near`
- **Enrichment (idempotent data backfill — columns already exist, no migration):** a static NUCC
  crosswalk (`taxonomy_code` → `taxonomy_description` + `specialty_codes`), plus deterministic
  `quality_rating`/`accepting_new_patients` for dev; enrich the demo plan's NY in-network providers
  near 40.7580,-73.9855. Implement in `services/quality_enrichment.py` + an idempotent
  `data/ingest` backfill (gated by `audit_source`).
- **Endpoint files:** `services/geo_search.py` (verbatim Haversine + `parse_wkt_point`),
  `api/v1/providers_near.py`, extend `schemas/provider.py` with `ProviderNearItem`
  (`ProviderOut` + `specialty?`, `distanceKm`, `inNetwork`, `acceptingNew?`, `qualityRating?`);
  `provider_repo.near_candidates(session, lat, lng, plan_id)` (LEFT JOIN `in_network` on `plan_id`+`npi`).
- **Contract:** `GET /api/v1/providers/near?specialty&lat&lng&radiusKm=25&inNetworkOnly=false&
  acceptingNewOnly=false&planId?&limit=50` → `{ total, query, providers:[ProviderNearItem] }`
  (ordered). `planId` required when `inNetworkOnly`.
- **Done:** `inspect eval eval/tasks/provider_lookup_eval.py` passes;
  `uv run pytest eval/tests/test_provider_lookup.py -q` green; integration `test_providers_near.py`
  (seeded NY query returns enriched in-network providers ordered by distance then quality).

### M9 — `POST /api/v1/providers/bulk`
- Files: `api/v1/providers_bulk.py`, schemas (`ProviderBulkRequest{npis[≤100]}`,
  `ProviderBulkResponse{providers}`); `provider_repo.get_providers_by_npis` (`WHERE npi = ANY(:npis)`).
- **Done:** unit + integration `test_providers_bulk.py` (bulk shape matches `/providers/{npi}`; missing NPIs omitted).

## Config (M1)

`core/config.py`: `default_radius_km: float = 25`, `near_max_limit: int = 50`.

## Constraints

- No PostGIS on the dev DB → all distance math is app-side; never emit `ST_DWithin`.
- Do **not** reimplement WS-1 loaders (`data/ingest/npi_ingest.py`, `care_compare_sync.py`,
  `mrf_parser.py`) — the service only **queries** `providers` + `in_network`.

## Future (out of scope now)

Production geo: migrate `providers.location` to PostGIS `geography(POINT,4326)` + GiST and swap the
Haversine filter for `ST_DWithin` (same `/providers/near` contract); live Care Compare refresh.
