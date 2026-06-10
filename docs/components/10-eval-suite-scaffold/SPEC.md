# Component 10 - Inspect AI Eval Suite Scaffold

> **Branch**: `feat/eval-scaffold`  |  **Day(s)**: 10  |  **Workstream**: WS-7/WS-8

## Goal & Scope

`just eval` runs the full Inspect AI suite against a model and produces a scored report.

**First task**: `coverage_qa_eval.py` — scores agent answers for exact + semantic match.

**First dataset**: 20 hand-written `(member_context, question, expected_answer)` tuples in `eval/datasets/golden_qa.json`.

**Pass threshold**: 0.85 semantic match.

**Output**: HTML report saved to `eval/reports/`.

**Out of scope**: card OCR eval, hallucination eval, provider lookup eval, e2e voice eval (later phases).

