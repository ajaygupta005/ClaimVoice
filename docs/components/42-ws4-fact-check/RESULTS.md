# Component 42 - WS-4 Fact-Check - Results

## Checklist

- [x] `schemas/fact_check.py` -- `FactCheckRequest { answer, facts, claimTypes }` and
      `FactCheckResponse { grounded, guardReason, ungroundedClaims, mode }`
      (camelCase Pydantic v2).
- [x] `services/fact_check.py::check_grounding_mock` -- deterministic matcher over
      `\$[\d,]+`, `Tier N`, and coverage booleans; amounts comma-normalised before
      comparison.
- [x] `services/fact_check.py::_check_with_claude` + `fact_check(...)` -- Claude
      entailment judge gated on `FACT_CHECK_MODE=claude` + `ANTHROPIC_API_KEY`, with
      mock fallback on any error; `mode` reports which path ran.
- [x] `POST /api/v1/fact_check` wired (reads `fact_check_mode` / `anthropic_api_key` /
      `anthropic_model` from Settings) and registered in `api/v1/__init__.py`; pure
      over payload, no DB.
- [x] (M7) `tests/conftest.py` -- session-scoped `client` fixture + auto-skip of
      integration tests when `DATABASE_URL` is unreachable.
- [x] (M7) `tests/integration/test_member_journey.py` -- end-to-end WS-4 journey
      (coverage -> cost -> formulary -> fact_check) for `CVX-0042-MT`.

## Tests

- Unit: `services/eligibility/tests/unit/test_fact_check.py` -- grounded vs
  ungrounded amounts / tiers / coverage flags; pure, no DB; asserts `mode="mock"` and
  `ungroundedClaims`.
- Integration: `services/eligibility/tests/integration/test_fact_check_endpoint.py`
  (`@pytest.mark.integration`, FastAPI `TestClient`) -- the `{grounded, guardReason,
  ungroundedClaims, mode}` contract for grounded and ungrounded answers.
- Member journey: `services/eligibility/tests/integration/test_member_journey.py`
  threads real coverage/cost/formulary `facts` through `/fact_check` and asserts the
  answer is grounded.
- Run via per-service ephemeral uv env (`PYTHONPATH=services/eligibility/src`); part
  of the WS-4 service suite that is green at **40 passed** total (unit run is fully
  offline; integration auto-skips without `DATABASE_URL`).

## Commit

```
acb3fcd feat(ws4): POST /fact_check (structured grounding backbone)
d2b0609 test(ws4): integration conftest + end-to-end member journey
```

## Notes

- `mock` is the default precisely because it is offline and deterministic -- this
  endpoint is on the critical path of every spoken answer, so it must always return a
  verdict without a key.
- `claude` mode is an advisory upgrade: wrapped in try/except, falling back to the
  matcher on timeout / rate-limit / malformed JSON; the `mode` field tells the caller
  which produced the verdict.
- This is the single grounding backbone WS-6's hallucination guard posts to; the
  facts it verifies are produced by Components 40-41 using matching `cents_to_usd` /
  `Tier N` phrasing, so the matcher and producers stay in agreement.
