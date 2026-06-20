# Component 46 - WS-6 Hallucination Guard

> **Branch**: feat/ws456-grounded-agent | **Milestone**: M11 | **Workstream**: WS-6

## Goal

Implement the real hallucination guard so every answer is verified grounded before
it is spoken.

- Implement `guards/hallucination.py` as the shared fact-check client:
  - `tool_mode="http"` → POST `{ answer, facts }` to WS-4
    `POST /api/v1/fact_check`; set `grounded` / `guard_reason` from the response.
  - `mock` (default) or any HTTP error → run the same matcher in-process,
    mirroring WS-4's mock fact_check: dollar amounts, formulary tiers (`Tier N`),
    and coverage booleans ("not covered", "prior authorization required").
- Rewire `graph/nodes/hallucination_guard.py` to call the guard over
  `tool_facts`, falling back to `[tool_result]` when no explicit facts are present.
- Preserve behavior: escalation still passes the guard, and the reason strings
  still contain `grounded` / `ungrounded` / `escalat` exactly where the existing
  tests assert them.

## Out of scope

- SBC-RAG grounding (pgvector retrieval of plan documents).
