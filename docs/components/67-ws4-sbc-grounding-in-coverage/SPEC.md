# Component 67 - WS-4 SBC Grounding in /coverage

> **Branch**: feat/live-product | **Workstream**: WS-4 | **Plan phase**: 2

## Goal

Surface SBC RAG passages as extra grounding facts on `GET /api/v1/coverage`, so the voice
agent's coverage answers can cite the plan's Summary-of-Benefits text (e.g. the MRI prior-
authorization clause) -- without changing the pure response builder or breaking offline
unit tests.

- Retrieve top-k SBC chunks for the member's plan + the queried service and append trimmed
  passages to the response `facts[]`.
- Best-effort: a no-op when SBC is disabled, no embed key is set, no chunks match, or any
  error occurs (structured grounding still answers).
- Bound the embedding client so a slow Azure call can never hang `/coverage`.

## Out of scope

- The embedding layer + ingest (Component 66).
- Consuming the facts in the voice answer / guard (Component 68 -- it flows automatically).
