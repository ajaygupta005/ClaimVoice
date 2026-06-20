# Component 44 - Provider Bulk Lookup - Research

## Why `WHERE npi = ANY(:npis)` over N round-trips
A client hydrating several providers (e.g. a list view, or the voice agent
resolving a set of referenced NPIs) would otherwise issue one
`GET /providers/{npi}` per NPI — N HTTP round-trips and N queries. A single
`POST /providers/bulk` with `WHERE npi = ANY(:npis)` collapses this to one request
and one indexed query. `= ANY(:npis)` binds the list as a single Postgres array
parameter, so there is no SQL string interpolation of the list and no per-NPI
statement. The `<= 100` cap (enforced by the Pydantic `ProviderBulkRequest`)
bounds the array size so a single request can't fan out unboundedly.

## Why omit-missing (sparse client hydration)
The endpoint returns only the NPIs that exist; unknown NPIs are dropped silently
rather than erroring or returning a null placeholder. Clients doing sparse
hydration typically already hold the NPI list and just want whatever data the
directory has — a partial result is more useful than a 404 that fails the whole
batch. Callers that care about absence compare the requested set against the
returned `npi`s (which the integration test does), so omit-missing keeps the
response shape clean while losing no information.

## Why reuse the `/providers/{npi}` row mapper
`providers_bulk` imports `_row_to_provider` from `api/v1/providers.py` and reuses
`_SELECT_COLS` via `provider_repo`, so a bulk item is **byte-identical** to the
single-detail response. This is asserted directly
(`test_bulk_shape_matches_detail`) and means clients can treat bulk and detail
results interchangeably with no separate schema.
