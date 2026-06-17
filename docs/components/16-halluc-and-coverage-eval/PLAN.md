# Component 16 - Hallucination + Coverage QA Evals - Plan

1. `eval/datasets/hallucination_golden.json` with 10 hand-written examples.
2. `eval/tasks/hallucination_eval.py` using `model_graded_qa` with a strict
   grader prompt.
3. Rewrite `eval/tasks/coverage_qa_eval.py` to use `system_message` +
   `model_graded_qa`.
4. Update `eval/README.md` with the two tasks.

