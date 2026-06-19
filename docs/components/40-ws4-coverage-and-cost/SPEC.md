# Component 40 - WS-4 Coverage & Cost

> **Branch**: feat/ws456-grounded-agent | **Milestone**: M3 + M4 | **Workstream**: WS-4

## Goal

Turn the eligibility service's structured plan data into the two answers the voice
agent needs most often: "is this covered, and how much will it cost?".

- `GET /api/v1/coverage` -- resolve a member's plan benefit for a service and return
  covered / copay / coinsurance / prior-auth, plus deductible and out-of-pocket
  remaining. Picks the best In-Network benefit row (name match preferred over
  service_category) and derives the booleans/amounts from it.
- `POST /api/v1/cost/estimate` -- copay / deductible / OOP math from the member's
  year-to-date spend and the plan levels. Returns a single copay when the matched
  benefit is copay-based, or a `$0 -> deductible-remaining` range when it is
  coinsurance-based.
- Every response carries a human-readable `facts: list[str]` so the fact-check guard
  (Component 42) and WS-6's hallucination guard can verify each spoken claim.
- Reproduce the golden values for demo member `CVX-0042-MT`: MRI is covered at 20%
  coinsurance and requires prior auth; deductible $1,500 total / $450 spent /
  $1,050 remaining; OOP $5,000 max / $1,200 spent / $3,800 remaining; urgent-care
  copay $75; PCP copay $30.

## Out of scope

- SBC RAG as an additional `facts` source (deferred -- needs a pgvector-capable
  Postgres + Voyage embeddings; the dev DB is plain Postgres).
- The fact-check / grounding verification itself (separate Component 42).
- Cost projections that model coinsurance once the deductible is met (the estimate
  is intentionally a conservative range).
