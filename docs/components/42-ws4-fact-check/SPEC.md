# Component 42 - WS-4 Fact-Check

> **Branch**: feat/ws456-grounded-agent | **Milestone**: M6 | **Workstream**: WS-4

## Goal

`POST /api/v1/fact_check` -- the hallucination-guard backbone for the whole product.
Given a candidate `answer` and the structured `facts` that backed it, decide whether
every factual claim in the answer is grounded.

- Verifies three claim types: dollar amounts (`$[\d,]+`), formulary tiers (`Tier N`),
  and coverage booleans (e.g. "not covered", "prior authorization required").
- `mock` mode (default, no key): a deterministic matcher -- every amount/tier/flag in
  the answer must be supported by `facts`. This is what runs in CI/dev, fully offline.
- `claude` mode (`FACT_CHECK_MODE=claude` + `ANTHROPIC_API_KEY`): an LLM entailment
  judge that returns grounded / ungrounded with a reason; it falls back to the mock
  matcher on any error so the endpoint never hard-fails.
- Response: `{ grounded, guardReason, ungroundedClaims[], mode }`.
- This is the single backbone WS-6's hallucination guard calls before any claim is
  spoken; coverage / cost / formulary (Components 40-41) are its grounding-string
  producers.

Also wired here (Milestone M7): a shared `tests/conftest.py` (session-scoped FastAPI
`TestClient` fixture + auto-skip of integration tests when no DB is reachable) and an
end-to-end `test_member_journey.py` that walks the full WS-4 member journey.

## Out of scope

- SBC RAG as a grounding source -- fact-check verifies against the supplied structured
  `facts` only (RAG is deferred; the dev DB has no pgvector).
- Claude / mock are advisory verifiers; they do not author or rewrite the answer.
