# Component 44 - Provider Bulk Lookup - Results

## Checklist

- [x] `services/providers/src/providers/schemas/provider.py` —
      `ProviderBulkRequest{ npis (1..100) }` + `ProviderBulkResponse{ providers }`.
- [x] `services/providers/src/providers/repositories/provider_repo.py` —
      `get_providers_by_npis` using `WHERE npi = ANY(:npis)` (returns `[]` for empty).
- [x] `services/providers/src/providers/api/v1/providers_bulk.py` —
      `POST /api/v1/providers/bulk`, shared `_row_to_provider` mapper reused.
- [x] `api/v1/__init__.py` — `providers_bulk` registered before `/providers/{npi}`.
- [x] Missing NPIs omitted from the response (no error / placeholder).

## Tests

- Integration: `services/providers/tests/integration/test_providers_bulk.py` —
  - `test_bulk_returns_requested_and_omits_missing`: 3 real NPIs + one bogus
    `"0000000000"`; all real NPIs returned, bogus one absent.
  - `test_bulk_shape_matches_detail`: a bulk item equals the `/providers/{npi}`
    detail (`npi`, `qualityRating`).
  - `test_bulk_rejects_empty_list`: empty `npis` -> 422 (`min_length=1`).
  Integration tests auto-skip when `DATABASE_URL` is unreachable.
- Part of the WS-5 service suite: 20 passed total (M8 + M9).

## Commit

```
eb17de3  feat(ws5): POST /providers/bulk (batch NPI lookup)
```

Files in the commit: `services/providers/src/providers/api/v1/__init__.py`,
`services/providers/src/providers/api/v1/providers_bulk.py`,
`services/providers/src/providers/schemas/provider.py`
(`get_providers_by_npis` added to `repositories/provider_repo.py` in this work),
`services/providers/tests/integration/test_providers_bulk.py`.

## Notes

- `= ANY(:npis)` binds the NPI list as a single Postgres array parameter — one
  query, no per-NPI round-trips and no SQL string interpolation.
- Bulk responses reuse the exact `/providers/{npi}` `ProviderOut` shape via the
  shared `_row_to_provider` mapper, so callers can treat bulk and detail items
  interchangeably.
- Omit-missing is intentional: a partial result serves sparse client hydration
  better than failing the whole batch on one unknown NPI.
- Route registration order matters — `/providers/bulk` and `/providers/near` are
  included before the dynamic `/providers/{npi}` so the static paths win.
