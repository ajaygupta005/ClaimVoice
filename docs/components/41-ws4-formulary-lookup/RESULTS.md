# Component 41 - WS-4 Formulary Lookup - Results

## Checklist

- [x] `member_repo.lookup_drug(session, member_id, drug, limit=5)` added (raw SQL via
      `text()` + `.mappings()`; exact-name-then-lowest-tier match; same-or-lower-tier
      alternatives excluding the match; `None` when the member does not exist).
- [x] `schemas/formulary.py::FormularyLookupResponse` added (camelCase Pydantic v2,
      reusing `FormularyDrugOut` for `match` and `alternatives`).
- [x] `services/formulary.py` -- `drug_out(row)` mapper and
      `build_formulary_lookup(member_id, result, query)` producing `onFormulary` and a
      `facts` list.
- [x] `GET /api/v1/formulary/lookup` wired via `db_session()` and registered in
      `api/v1/__init__.py`.
- [x] Golden values reproduced for `CVX-0042-MT`: lisinopril -> Tier 1, prior auth
      false; Humira -> Tier 4, prior auth true, with lisinopril among the lower-tier
      alternatives.

## Tests

- Unit: `services/eligibility/tests/unit/test_formulary_lookup.py` --
  `build_formulary_lookup` over hand-built result dicts (no DB); asserts match tiers,
  prior-auth flags, `facts`, and the off-formulary (`onFormulary=false`) path.
- Integration:
  `services/eligibility/tests/integration/test_formulary_lookup_endpoint.py`
  (`@pytest.mark.integration`, FastAPI `TestClient`, auto-skip when `DATABASE_URL`
  unreachable) -- lisinopril and Humira lookups against the seeded Sentinel DB,
  including the lower-tier alternative.
- Run via per-service ephemeral uv env (`PYTHONPATH=services/eligibility/src`); part
  of the WS-4 service suite that is green at **40 passed** total.

## Commit

```
976cb1a feat(ws4): GET /formulary/lookup + alternatives
```

## Notes

- "Alternatives" is a pure tier-cost heuristic (same-or-lower tier, cheaper/equal),
  not a clinical substitution -- the seeded data has no drug-class metadata, so we
  only claim what tier supports.
- The `drug_out` mapper is shared with the existing `/formulary/search` presentation
  so both endpoints render a drug row identically; `lookup_drug` reuses the same
  `ILIKE` + tier-ordering SQL pattern as `search_formulary`.
