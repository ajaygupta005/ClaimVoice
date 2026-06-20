# Component 43 - Provider Geo Search + Enrichment - Results

## Checklist

- [x] `services/providers/src/providers/services/geo_search.py` — `haversine_km`
      (verbatim), `parse_wkt_point`, `rank_near`.
- [x] `services/providers/src/providers/services/quality_enrichment.py` —
      `NUCC_CROSSWALK`, `classify`, `derive_quality`, `derive_accepting_new`.
- [x] `services/providers/src/providers/schemas/provider.py` — `ProviderNearItem`
      (`ProviderOut` + `distanceKm`, `inNetwork`, `specialty?`) + `ProviderNearResponse`.
- [x] `services/providers/src/providers/repositories/provider_repo.py` —
      `near_candidates` with `EXISTS(... in_network ...)` on `plan_id` + `npi`.
- [x] `services/providers/src/providers/api/v1/providers_near.py` —
      `GET /api/v1/providers/near` reproducing the pinned eval ranking.
- [x] `api/v1/__init__.py` — `providers_near` registered before `/providers/{npi}`
      (route-shadowing fix).
- [x] `data/ingest/enrich_providers.py` — idempotent backfill (updates only rows
      where `taxonomy_description IS NULL`), wired into `scripts/seed_dev.{ps1,sh}`.
- [x] No eval files edited; `eval/tasks/provider_lookup_eval.py` ranking reproduced.

## Tests

- Unit: `services/providers/tests/unit/test_geo_search.py` — `parse_wkt_point`,
  zero/positive Haversine, specialty substring, radius, in-network, accepting-new,
  and distance-then-quality sort.
- Integration: `services/providers/tests/integration/test_providers_near.py` —
  seeded query near Midtown (40.7580, -73.9855) returns enriched matches ordered by
  distance (all within radius, specialty substring holds); in-network-only against the
  demo plan returns only in-network providers; in-network-only without `planId` -> 400.
  Integration tests auto-skip when `DATABASE_URL` is unreachable (`tests/conftest.py`).
- Pinned eval contract stays green: `eval/tests/test_provider_lookup.py`.
- WS-5 service suite: 20 passed total (across M8 + M9).

## Commit

```
5a8a024  feat(ws5): enrich providers + GET /providers/near (eval-exact ranking)
```

Files in the commit: `data/ingest/enrich_providers.py`, `scripts/seed_dev.ps1`,
`scripts/seed_dev.sh`, `services/providers/pyproject.toml`,
`services/providers/src/providers/api/v1/{__init__.py,providers_near.py}`,
`services/providers/src/providers/repositories/provider_repo.py`,
`services/providers/src/providers/schemas/provider.py`,
`services/providers/src/providers/services/{geo_search.py,quality_enrichment.py}`,
`services/providers/tests/conftest.py`,
`services/providers/tests/integration/test_providers_near.py`,
`services/providers/tests/unit/test_geo_search.py`.

## Notes

- `near_candidates` returns `in_network=false` whenever `plan_id` is absent — the
  endpoint rejects `inNetworkOnly` without `planId` (400) so this is never ambiguous.
- `rank_near` matches specialty over both `taxonomy_description` and the joined
  `specialty_codes` text, so a query like `"cardio"` matches `"Cardiology"`.
- Enrichment is a data backfill, not a migration — the five columns already exist;
  re-running the backfill is a no-op and never clobbers Care-Compare ratings.
- Production geo (`ST_DWithin` on a PostGIS `geography` column) keeps this same
  contract and remains deferred (see Known limitations in `Plan/HANDOFF.md`).
