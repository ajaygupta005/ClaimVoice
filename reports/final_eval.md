# ClaimVoice — Eval Report

Generated from the Inspect AI suite (`just eval`). Fill in numbers after a run.

## How to reproduce

```bash
export ANTHROPIC_API_KEY=sk-...
just eval                                            # all tasks
inspect eval eval/tasks/provider_lookup_eval.py      # provider ranking (no key needed)
inspect eval eval/tasks/agent_pipeline_eval.py       # agent pipeline (deterministic)
inspect eval eval/tasks/coverage_qa_eval.py          # coverage QA (needs key)
inspect eval eval/tasks/hallucination_eval.py        # hallucination (needs key)
```

## Scorecard

| Task | Metric | Target | Result |
| --- | --- | --- | --- |
| provider_lookup_eval | ranking accuracy | 1.00 | ___ |
| agent_pipeline_eval | deterministic pass rate | >= 0.90 | ___ |
| coverage_qa_eval | model-graded accuracy | >= 0.94 | ___ |
| hallucination_eval | grounded rate | >= 0.995 | ___ |

## Notes

- `provider_lookup_eval` and `agent_pipeline_eval` run with no API key (pure
  deterministic scorers), so they gate every CI run cheaply.
- `coverage_qa_eval` and `hallucination_eval` use Claude as a judge and only
  run when `ANTHROPIC_API_KEY` is set (nightly, or manually).

## Cost (fill after a run)

- Total tokens: ___
- Total cost: $___
- Wall-clock: ___
