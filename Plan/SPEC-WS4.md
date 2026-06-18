# SPEC — WS-4 Eligibility & Plan Knowledge

> Service: `services/eligibility` (FastAPI, port 8002). Milestones M1, M3–M7.
> Grounding source for the whole product: coverage, cost, formulary, and the **fact-check** backbone
> the voice agent's hallucination guard calls. **Structured data only** (SBC RAG deferred).

## Current state (baseline)

- 3 real GET endpoints already work: `/api/v1/members/{id}/summary`, `/api/v1/plans/{id}/benefits`,
  `/api/v1/formulary/search`, backed by `repositories/member_repo.py` (raw SQL via `text()` +
  `.mappings()`, dict rows; camelCase Pydantic v2 schemas; `lib/db.py` `db_session()`).
- All `services/*.py` are 1-line stubs (x12_stub, plan_graph, cost_estimator, formulary, sbc_rag,
  fact_check, audit). No `/fact_check` endpoint.
- Alembic wired; schema in `alembic/versions/001_init_schema.py` (PostGIS-optional; pgvector deferred).
- DB seeded (plans, plan_benefits, formulary_drug, members, in_network, icd10/hcpcs).

## Conventions / reuse

- **Money = integer cents (BIGINT).** Add `lib/money.py` (`cents_to_usd(c) -> "$1,500"`).
- Reuse `db_session()`, `member_repo.get_member_with_plan/get_plan_benefits/search_formulary`,
  the camelCase schema style, and `core/config.py` Settings.
- Every new endpoint returns a `facts: list[str]` of human-readable claim strings that
  `/fact_check` (and WS-6's guard) can verify against.

## Deliverables & milestones

### M1 — deps + config
- `pyproject.toml`: add `anthropic>=0.40`.
- `core/config.py`: add `anthropic_api_key=""`, `anthropic_model="claude-sonnet-4-6"`,
  `fact_check_mode: Literal["mock","claude"]="mock"`.

### M3 — `GET /api/v1/coverage`
- Files: `api/v1/coverage.py`, `schemas/coverage.py`, `lib/money.py`; `member_repo.get_coverage`;
  real `services/coverage.py` (pick In-Network benefit row; derive covered/coinsurance/copay/PA/
  deductible-remaining).
- **Contract:** `?memberId&service&networkType="In Network"` →
  ```
  CoverageResponse { memberId, planId, service, matchedBenefit?, covered, networkType,
    copayAmountCents?, coinsurancePercentage?, requiresPriorAuth,
    deductibleRemainingCents, oopRemainingCents, facts[] }
  ```
- **Done:** unit `test_coverage_schema.py`; integration `test_coverage_endpoint.py`
  (demo plan MRI → `requiresPriorAuth=true`, `coinsurancePercentage=20`).

### M4 — `POST /api/v1/cost/estimate`
- Files: `api/v1/cost.py`, `schemas/cost.py`; `member_repo.get_cost_inputs`; real `services/cost_estimator.py`.
- Math: `deductibleRemaining = max(0, individual_deductible - deductible_ytd)`; same for OOP; copay
  from the matched benefit; coinsurance estimate when no copay.
- **Contract:** `{ memberId, costType:["copay"|"deductible"|"oop"|"service"], service? }` →
  ```
  CostEstimateResponse { memberId, costType, copayAmountCents?,
    deductibleTotalCents?, deductibleSpentCents?, deductibleRemainingCents?,
    oopMaxCents?, oopSpentCents?, oopRemainingCents?,
    estimateLowCents?, estimateHighCents?, facts[] }
  ```
- **Done (demo member `CVX-0042-MT`):** deductible 150000/45000/105000; OOP 500000/120000/380000;
  urgent-care copay 7500; PCP copay 3000.

### M5 — `GET /api/v1/formulary/lookup`
- Files: `api/v1/formulary_lookup.py`, extend `schemas/formulary.py`
  (`FormularyLookupResponse` = best `match` + tier-ranked `alternatives`); `member_repo.lookup_drug`;
  real `services/formulary.py`. Reuse existing `search_formulary` SQL.
- **Contract:** `?memberId&drug&limit=5` →
  `{ memberId, planId, query, match?:FormularyDrugOut, alternatives[], onFormulary, facts[] }`.
- **Done:** lisinopril → Tier 1, PA false; Humira → Tier 4, PA true.

### M6 — `POST /api/v1/fact_check` (structured grounding backbone)
- Files: `api/v1/fact_check.py`, `schemas/fact_check.py`, real `services/fact_check.py`.
- **Mock mode** (default, no key): extract `\$[\d,]+`, `Tier \d`, and coverage booleans from `answer`;
  each must be supported by `facts`. **Claude mode** (`fact_check_mode=claude` + key): entailment judge.
- **Contract:** `{ answer, facts[], claimTypes=["amount","tier","boolean"] }` →
  `{ grounded, guardReason, ungroundedClaims[], mode }`.
- **Done:** unit `test_fact_check.py` (grounded vs ungrounded amounts/tiers/flags). Pure over payload — no DB.

### M7 — integration tests + eval wiring
- `services/eligibility/tests/integration/` — `@pytest.mark.integration`, FastAPI `TestClient`,
  `DATABASE_URL`→Sentinel, auto-skip when DB unreachable (mirror telephony skip-guards). Cover all endpoints.
- **Done:** `uv run pytest services/eligibility -m integration -q` green;
  `inspect eval eval/tasks/coverage_qa_eval.py` and `hallucination_eval.py` run (model-graded; need key).

## Future (out of scope now)

SBC RAG: `002_sbc_embeddings` migration (pgvector + `sbc_chunk` table), Voyage `voyage-3-large`
embeddings, retrieval added as a `facts` source in `/coverage` + `/fact_check`. Requires a
pgvector-capable Postgres.
