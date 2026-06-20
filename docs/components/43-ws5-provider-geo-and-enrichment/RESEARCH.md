# Component 43 - Provider Geo Search + Enrichment - Research

## Why Haversine app-side (no PostGIS on the dev DB)
The dev DB is Sentinel's plain `postgres:16-alpine` (the project's own `postgis`
image fails to pull in this environment), so there is **no PostGIS and no
pgvector**. `ST_DWithin` is therefore unavailable. We store `providers.location`
as text WKT (`POINT(lng lat)`) and compute great-circle distance in Python. The
production path (migrate to `geography(POINT,4326)` + GiST + `ST_DWithin`) keeps
the same `/providers/near` contract and is deferred.

## Why copy `_haversine_km` verbatim
`eval/tasks/provider_lookup_eval.py` is the **pinned contract** for ranking — its
`rank_providers` + `_haversine_km` + `score_case` are the reference, exercised by
7 golden cases and `eval/tests/test_provider_lookup.py`. Copying the function
byte-for-byte into `services/geo_search.py` (rather than re-deriving the formula)
guarantees the live endpoint produces the same distances and therefore the same
ordering as the eval. We do not edit the eval files; they stay green as the
contract test.

## Why a static NUCC crosswalk + deterministic derived quality/accepting-new
The NPPES sample only populates `taxonomy_code`; `taxonomy_description`,
`specialty_codes`, `quality_rating`, and `accepting_new_patients` are NULL for all
500 providers. Without specialty text the substring filter matches nothing, and
without quality the tiebreak is meaningless. A small hand-curated `NUCC_CROSSWALK`
maps the codes that actually appear (plus common extras) to a human specialty
label + `specialty_codes`. `quality_rating` and `accepting_new_patients` are
derived **deterministically from the NPI** (`quality` in `[3.0, 5.0]`,
`accepting_new` ~75%), so dev data is reproducible across machines and seeds —
important because the integration tests assert ordering and in-network shape
against whatever the seed produced.

## Why enrichment is an idempotent data backfill (no migration)
The five enrichment columns **already exist** in the `providers` schema (WS-1
owns the DDL); they are simply NULL. So enrichment is a data backfill, not a
schema change — no Alembic migration. `data/ingest/enrich_providers.py` updates
only rows `WHERE taxonomy_description IS NULL`, which makes re-runs no-ops and
also avoids clobbering any real Care-Compare-sourced rating on already-enriched
rows. It reuses `quality_enrichment` as the single source of truth for the
crosswalk and is wired into `scripts/seed_dev.{ps1,sh}` after the WS-1 loaders.

## The route-ordering gotcha (`/providers/near` shadowed by `/providers/{npi}`)
The existing detail route `GET /providers/{npi}` is a dynamic path; if registered
first, FastAPI matches `/providers/near` as `{npi}="near"` and the static route is
never reached. Fix: in `api/v1/__init__.py`, include `providers_near` (and later
`providers_bulk`) routers **before** the dynamic `providers` detail router so the
static paths win.
