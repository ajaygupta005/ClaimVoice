# Component 10 - Inspect AI Eval Suite Scaffold - Implementation Plan

> Step-by-step. Check off as you go.

1. [ ] Author `eval/pyproject.toml` with `inspect-ai`, `anthropic`, `langfuse` as deps.
2. [ ] Hand-write 20 golden Q&A pairs in `eval/datasets/golden_qa.json` covering:
    - Coverage questions ("Is X covered?")
    - Cost questions ("How much for X?")
    - Provider questions ("Find a Y near me")
3. [ ] Author `eval/tasks/coverage_qa_eval.py` as an Inspect AI Task:
    - load dataset
    - solver: call the agent (stub for now)
    - scorer: exact-match + semantic-similarity threshold
4. [ ] Wire `just eval` recipe to `inspect eval eval/tasks/`.
5. [ ] Author `eval/README.md` documenting how to add new tasks.
6. [ ] Run `just eval` once and confirm a score lands in `eval/reports/`.
7. [ ] Commit with message `feat(eval): inspect ai eval suite scaffold`.

