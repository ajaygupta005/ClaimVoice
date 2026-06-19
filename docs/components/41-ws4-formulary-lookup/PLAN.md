# Component 41 - WS-4 Formulary Lookup - Plan

1. Add `member_repo.lookup_drug(session, member_id, drug, limit=5)` to
   `services/eligibility/src/eligibility/repositories/member_repo.py`
   (raw SQL via `text()` + `.mappings()`):
   - Resolve the member's `plan_id`; return `None` if the member does not exist.
   - Best `match`: `WHERE plan_id = :pid AND drug_name ILIKE %drug%`, ordered by
     exact-name-match first (`CASE WHEN drug_name ILIKE :exact THEN 0 ELSE 1 END`),
     then `formulary_tier NULLS LAST`, then `drug_name`, `LIMIT 1`.
   - `alternatives`: only when the match has a non-null tier --
     `WHERE plan_id = :pid AND id != :match_id AND formulary_tier IS NOT NULL
     AND formulary_tier <= :tier ORDER BY formulary_tier, drug_name LIMIT :limit`.
   - Return `{plan_id, match|None, alternatives[]}`.

2. Extend `services/eligibility/src/eligibility/schemas/formulary.py` with
   `FormularyLookupResponse { memberId, planId, query, match?: FormularyDrugOut,
   alternatives: list[FormularyDrugOut], onFormulary, facts[] }` (reusing the existing
   camelCase `FormularyDrugOut`).

3. Implement in `services/eligibility/src/eligibility/services/formulary.py`:
   - `drug_out(row)` -- snake_case `formulary_drug` row -> `FormularyDrugOut` (shared
     by the match and each alternative).
   - `build_formulary_lookup(member_id, result, query)` -- set
     `onFormulary = match is not None`; build `facts`
     (`"<drug> is on formulary, Tier N"`, `"prior authorization required"`,
     `"step therapy required"`, or `"<query> is not on the plan formulary"`); map the
     match and alternatives via `drug_out`.

4. Add the route `services/eligibility/src/eligibility/api/v1/formulary_lookup.py`
   (`GET /api/v1/formulary/lookup?memberId&drug&limit=5`) using
   `lib/db.py::db_session()` -> `lookup_drug` -> `build_formulary_lookup`; register the
   router in `api/v1/__init__.py`.

5. Unit test `services/eligibility/tests/unit/test_formulary_lookup.py` -- call
   `build_formulary_lookup` with hand-built result dicts (no DB): assert lisinopril
   match maps to Tier 1 / PA false, Humira to Tier 4 / PA true with the right `facts`,
   and an off-formulary query -> `onFormulary=false`.

6. Integration test
   `services/eligibility/tests/integration/test_formulary_lookup_endpoint.py`
   (`@pytest.mark.integration`, FastAPI `TestClient`, auto-skip without DB) -- against
   the seeded Sentinel DB for `CVX-0042-MT`: lisinopril -> Tier 1, no PA; Humira ->
   Tier 4, PA true, with lisinopril among the alternatives.
