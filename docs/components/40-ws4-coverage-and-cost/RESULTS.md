# Component 40 - WS-4 Coverage & Cost - Results

## Checklist

- [x] `lib/money.py::cents_to_usd` added (`150000 -> "$1,500"`, `12345 -> "$123.45"`,
      `None -> ""`).
- [x] `member_repo.get_coverage` + `member_repo.get_cost_inputs` added (raw SQL via
      `text()` + `.mappings()`; representative plan levels via `MAX(...)` over
      In-Network benefit rows; `None` when the member does not exist).
- [x] `schemas/coverage.py::CoverageResponse` and `schemas/cost.py::
      CostEstimateRequest`/`CostEstimateResponse` (camelCase Pydantic v2).
- [x] `services/coverage.py::build_coverage_response` derives
      covered/copay/coinsurance/prior-auth + deductible & OOP remaining and a `facts`
      list.
- [x] `services/cost_estimator.py::build_cost_estimate` does copay / deductible / OOP
      math and a copay-vs-coinsurance estimate range.
- [x] `GET /api/v1/coverage` and `POST /api/v1/cost/estimate` wired via `db_session()`
      and registered in `api/v1/__init__.py`.
- [x] Golden `CVX-0042-MT` values reproduced: MRI 20% coinsurance + prior auth;
      deductible 150000/45000/105000 cents; OOP 500000/120000/380000 cents;
      urgent-care copay 7500; PCP copay 3000.

## Tests

- Unit: `services/eligibility/tests/unit/test_coverage.py`,
  `services/eligibility/tests/unit/test_cost.py` -- pure over hand-built result dicts,
  no DB; assert structured fields, golden cents, and `facts` content.
- Integration: `services/eligibility/tests/integration/test_coverage_endpoint.py`,
  `services/eligibility/tests/integration/test_cost_endpoint.py`
  (`@pytest.mark.integration`, FastAPI `TestClient`, auto-skip when `DATABASE_URL`
  unreachable) -- MRI -> `requiresPriorAuth=true`, `coinsurancePercentage=20`;
  deductible/OOP remaining and PCP/urgent-care copays against the seeded Sentinel DB.
- Run via per-service ephemeral uv env (`PYTHONPATH=services/eligibility/src`); part
  of the WS-4 service suite that is green at **40 passed** total.

## Commit

```
36f16b8 feat(ws4): GET /coverage (structured benefit lookup)
2dcdb22 feat(ws4): POST /cost/estimate (copay/deductible/OOP math)
```

## Notes

- Plan-level deductible/OOP are computed as `MAX` over In-Network benefit rows
  because those values live per-benefit in the seeded schema, not once per plan; this
  lets `costType: "deductible"`/`"oop"` answer without a service match.
- Coinsurance estimates are returned as a `$0 .. deductible-remaining` range rather
  than a fabricated point estimate, so the fact-check guard (Component 42) never has
  to reject an invented figure.
- All money stays integer cents until `cents_to_usd` formats it at the response
  boundary; the same USD strings appear in `facts`, which is what the guard regex
  verifies.
