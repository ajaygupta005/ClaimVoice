# Component 42 - WS-4 Fact-Check - Plan

1. Add `services/eligibility/src/eligibility/schemas/fact_check.py` (camelCase
   Pydantic v2):
   - `FactCheckRequest { answer, facts: list[str]=[], claimTypes:
     list[str]=["amount","tier","boolean"] }`.
   - `FactCheckResponse { grounded, guardReason, ungroundedClaims: list[str], mode }`.

2. Implement `services/eligibility/src/eligibility/services/fact_check.py`:
   - `check_grounding_mock(answer, facts, claim_types) -> (grounded, ungrounded[])` --
     compile `_AMOUNT = \$[\d,]+(?:\.\d{2})?` and `_TIER = [Tt]ier \d+`; join+lowercase
     the facts (and a comma-stripped copy for amounts); for each enabled claim type,
     collect any token in the answer not supported by the facts. Booleans: flag
     "not covered" / "prior authorization required" when the facts say otherwise.
   - `_check_with_claude(answer, facts, api_key, model)` -- lazy-import `anthropic`,
     prompt for a strict JSON entailment verdict, parse `{grounded, ungrounded,
     reason}`, return a `FactCheckResponse` with `mode="claude"`. Raises on any error.
   - `fact_check(answer, facts, claim_types, mode="mock", api_key="",
     model="claude-sonnet-4-6")` -- if `mode == "claude"` and a key is present, try
     Claude and fall back to the matcher on exception; otherwise run the matcher and
     return `mode="mock"`.

3. Add the route `services/eligibility/src/eligibility/api/v1/fact_check.py`
   (`POST /api/v1/fact_check`) reading `fact_check_mode`, `anthropic_api_key`, and
   `anthropic_model` from `core/config.py` Settings; register the router in
   `api/v1/__init__.py`. (No DB -- the endpoint is pure over its payload.)

4. Unit test `services/eligibility/tests/unit/test_fact_check.py` -- grounded vs
   ungrounded amounts, tiers, and coverage flags through `check_grounding_mock` /
   `fact_check`; assert `mode="mock"` and the `ungroundedClaims` contents.

5. Integration test
   `services/eligibility/tests/integration/test_fact_check_endpoint.py`
   (`@pytest.mark.integration`, FastAPI `TestClient`) -- POST grounded and ungrounded
   answers and assert the `{grounded, guardReason, ungroundedClaims, mode}` contract.

6. (M7) Add `services/eligibility/tests/conftest.py` -- a session-scoped `client`
   fixture (FastAPI `TestClient` over `eligibility.main:app`) and
   `pytest_collection_modifyitems` that auto-skips `@pytest.mark.integration` tests
   when `DATABASE_URL` is unset/unreachable (psycopg connect probe), mirroring the
   telephony skip-guards.

7. (M7) Add `services/eligibility/tests/integration/test_member_journey.py` -- an
   end-to-end WS-4 journey for `CVX-0042-MT`: coverage -> cost -> formulary, then
   feed the produced `facts` into `POST /api/v1/fact_check` and assert the composed
   answer is grounded.
