# Component 44 - Provider Bulk Lookup - Plan

1. `services/providers/src/providers/schemas/provider.py`: add
   `ProviderBulkRequest{ npis: list[str] (min_length=1, max_length=100) }` and
   `ProviderBulkResponse{ providers: list[ProviderOut] }`.
2. `services/providers/src/providers/repositories/provider_repo.py`: add
   `get_providers_by_npis(session, npis)` -> `SELECT _SELECT_COLS FROM providers
   WHERE npi = ANY(:npis)`; return `[]` for an empty list (no query).
3. `services/providers/src/providers/api/v1/providers_bulk.py`: `POST
   /providers/bulk` taking `ProviderBulkRequest`, calling `get_providers_by_npis`,
   and mapping rows with the shared `_row_to_provider` from `api/v1/providers.py`
   into `ProviderBulkResponse`.
4. `services/providers/src/providers/api/v1/__init__.py`: include the
   `providers_bulk` router **before** the dynamic `providers` detail router (same
   route-shadowing fix as `/providers/near`).
5. Tests: `services/providers/tests/integration/test_providers_bulk.py` — returns
   requested NPIs and omits a bogus one; bulk item shape matches `/providers/{npi}`;
   empty `npis` list rejected with 422 (`min_length=1`).
