# Component 16 - Hallucination + Coverage QA Evals

> **Branch**: `feat/eval-halluc-and-coverage` | **Day(s)**: 18, 21 | **Workstream**: WS-7

## Goal

Two real Inspect AI tasks (replacing the scaffolding from commit 10):

1. `coverage_qa_eval` -- 20 golden coverage questions, model-graded.
2. `hallucination_eval` -- 10 plan contexts where the agent must use ONLY
   the facts in the context. A judge model checks for unsupported claims.

## Out of scope

- Provider lookup eval (Phase 4).
- E2E voice eval (Phase 4).

