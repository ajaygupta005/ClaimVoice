# Component 40 - WS-4 Coverage & Cost - Plan

1. Add `services/eligibility/src/eligibility/lib/money.py` with
   `cents_to_usd(cents: int | None) -> str` (whole-dollar amounts drop `.00`;
   `None -> ""`). This is the single formatter both the structured fields and the
   `facts` strings use.

2. Extend `services/eligibility/src/eligibility/repositories/member_repo.py`
   (raw SQL via `text()` + `.mappings()`, dict rows):
   - `get_coverage(session, member_id, service, network_type="In Network")` ->
     `{member, benefit|None, plan_deductible_cents, plan_oop_cents}`. The benefit is
     the best row where `benefit_name ILIKE %service%` or `service_category ILIKE
     %service%`, ordered so a name match wins, `LIMIT 1`. Plan levels are
     `MAX(individual_deductible_cents)` / `MAX(out_of_pocket_max_cents)` over the
     plan's In-Network rows. Returns `None` if the member does not exist.
   - `get_cost_inputs(session, member_id, service=None, network_type="In Network")` ->
     `{member, plan_deductible_cents, plan_oop_cents, benefit|None}`; the benefit is
     resolved only when `service` is supplied.

3. Add `services/eligibility/src/eligibility/schemas/coverage.py` -- camelCase
   Pydantic v2 `CoverageResponse { memberId, planId, service, matchedBenefit?,
   covered, networkType, copayAmountCents?, coinsurancePercentage?, requiresPriorAuth,
   deductibleRemainingCents, oopRemainingCents, facts[] }`.

4. Add `services/eligibility/src/eligibility/schemas/cost.py` --
   `CostEstimateRequest { memberId, costType: Literal["copay","deductible","oop",
   "service"]="service", service? }` and `CostEstimateResponse` (copay /
   deductible{Total,Spent,Remaining} / oop{Max,Spent,Remaining} / estimate{Low,High}
   all optional cents, plus `facts[]`).

5. Implement `services/eligibility/src/eligibility/services/coverage.py`
   `build_coverage_response(result, service, network_type)`:
   `covered = benefit is not None`; pull copay / coinsurance / prior-auth from the
   matched row; `ded_remaining = max(0, plan_ded - member.deductible_ytd_cents)` and
   the same for OOP; build the `facts` list (`"<benefit> is covered (<network>)"`,
   `"copay $X"`, `"N% coinsurance"`, `"prior authorization required"`, deductible /
   OOP remaining).

6. Implement `services/eligibility/src/eligibility/services/cost_estimator.py`
   `build_cost_estimate(result, cost_type, service)`: branch on `cost_type`.
   `deductible` / `oop` emit the total/spent/remaining triplet; `copay`/`service`
   return the copay as a degenerate range when copay-based, or
   `estimateLow=0 .. estimateHigh=deductibleRemaining` when coinsurance-based.

7. Wire the routes: `services/eligibility/src/eligibility/api/v1/coverage.py`
   (`GET /api/v1/coverage?memberId&service&networkType`) and
   `services/eligibility/src/eligibility/api/v1/cost.py`
   (`POST /api/v1/cost/estimate`), both using `lib/db.py::db_session()`; register
   both routers in `api/v1/__init__.py`.

8. Unit tests `tests/unit/test_coverage.py` and `tests/unit/test_cost.py` -- call the
   `build_*` services with hand-built result dicts (no DB) and assert the golden
   `CVX-0042-MT` values and the shape of `facts`.

9. Integration tests `tests/integration/test_coverage_endpoint.py` and
   `tests/integration/test_cost_endpoint.py` (`@pytest.mark.integration`, FastAPI
   `TestClient`, auto-skip when `DATABASE_URL` is unreachable) -- hit the live
   endpoints against the seeded Sentinel DB and assert MRI -> `requiresPriorAuth
   true` / `coinsurancePercentage 20`, deductible/OOP and PCP/urgent-care copays.
