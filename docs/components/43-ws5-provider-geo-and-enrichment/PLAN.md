# Component 43 - Provider Geo Search + Enrichment - Plan

1. `services/providers/src/providers/services/geo_search.py`: add `haversine_km`
   (verbatim from `eval/tasks/provider_lookup_eval._haversine_km`), `parse_wkt_point`
   (`'POINT(lng lat)'` -> `(lat, lng)`, `None` on bad input), and `rank_near(query,
   candidates)` mirroring `rank_providers` — specialty substring over
   `taxonomy_description` / `specialty_codes`, radius filter, optional in-network /
   accepting-new filters, sort `(distance asc, quality desc)`.
2. `services/providers/src/providers/services/quality_enrichment.py`: add
   `NUCC_CROSSWALK` (`taxonomy_code` -> `(specialty label, specialty_codes)`),
   `classify(taxonomy_code)`, `derive_quality(npi)` (deterministic `[3.0, 5.0]`),
   `derive_accepting_new(npi)` (deterministic ~75%).
3. `services/providers/src/providers/schemas/provider.py`: add
   `ProviderNearItem(ProviderOut + distanceKm, inNetwork, specialty?)` and
   `ProviderNearResponse{ total, query, providers }`.
4. `services/providers/src/providers/repositories/provider_repo.py`: add
   `near_candidates(session, plan_id)` selecting `_SELECT_COLS` + `location` + an
   `EXISTS(... in_network ...)` boolean (LEFT-JOIN-style) for the given `plan_id`,
   over `WHERE location IS NOT NULL`.
5. `services/providers/src/providers/api/v1/providers_near.py`: `GET /providers/near`
   with query params, `radiusKm`/`limit` defaults from `core/config`
   (`default_radius_km=25`, `near_max_limit=50`), 400 when `inNetworkOnly` and no
   `planId`, then `near_candidates` -> `rank_near` -> `[:limit]` -> `ProviderNearItem`s.
6. `services/providers/src/providers/api/v1/__init__.py`: include `providers_near`
   router **before** the dynamic `providers` detail router (fix route shadowing).
7. `data/ingest/enrich_providers.py`: idempotent backfill — `SELECT npi,
   taxonomy_code FROM providers WHERE taxonomy_description IS NULL`, then `UPDATE`
   each row with `classify` + `derive_quality` + `derive_accepting_new`; reuse the
   `quality_enrichment` crosswalk via `sys.path` into the providers service.
8. Wire the backfill into `scripts/seed_dev.ps1` and `scripts/seed_dev.sh` after the
   WS-1 loaders so a fresh seed produces enriched providers.
9. Tests: `services/providers/tests/unit/test_geo_search.py` (parse/haversine/filters/
   sort) and `services/providers/tests/integration/test_providers_near.py` (seeded NY
   query near Midtown; in-network-only requires plan). Confirm the pinned
   `eval/tests/test_provider_lookup.py` stays green (no eval files touched).
