# Eval suite

Inspect AI tasks that score the agent.

## Tasks

| Task | What it measures | API key needed |
| --- | --- | --- |
| `agent_pipeline_eval` | LangGraph agent pipeline — intent, tool, answer, guard, escalation | No (deterministic gate) |
| `coverage_qa_eval` | Accuracy on 20 golden coverage Q&A pairs | Yes (LLM judge) |
| `hallucination_eval` | Whether the agent states a coverage fact not in the plan context | Yes (LLM judge) |

## Run

```bash
# Deterministic agent pipeline eval — no API key required
uv run pytest eval/tests/test_agent_pipeline_scorer.py   # scorer unit tests
uv run pytest eval/tests/test_agent_pipeline_dataset.py  # dataset shape tests
inspect eval eval/tasks/agent_pipeline_eval.py           # full Inspect AI run

# Optional: add LLM judge on top of the deterministic gate
ANTHROPIC_API_KEY=sk-... inspect eval eval/tasks/agent_pipeline_eval.py --model claude-sonnet-4-6

# Existing prompt-based evals (require ANTHROPIC_API_KEY)
just eval
inspect eval eval/tasks/coverage_qa_eval.py
inspect eval eval/tasks/hallucination_eval.py
```

## Deterministic vs LLM scoring (`agent_pipeline_eval`)

The `agent_pipeline_eval` task has two scoring layers:

1. **Deterministic scorer** (always runs, no API key):
   - Checks expected intent, tool, required phrases, forbidden phrases, grounded flag, escalation flag.
   - Produces pass/fail with human-readable failure reasons.
   - Acts as the required local gate — a case must pass this to be considered correct.

2. **LLM judge** (advisory, runs only when `ANTHROPIC_API_KEY` is set):
   - Judges whether the answer is factually sensible and member-friendly.
   - Does not override the deterministic score — it is logged separately.
   - Intended for use in CI or nightly eval runs before real Claude integration (C35+).

## Pipeline adapter

`eval/tasks/agent_pipeline_eval.py` exports `run_case()` and `score_case()` as
standalone functions importable without `inspect-ai`:

```python
from agent_pipeline_eval import run_case, score_case, load_cases
result = run_case("Is an MRI covered?")
sr = score_case(case_dict, result)
```

## Datasets

| Dataset | What it contains |
| --- | --- |
| `agent_pipeline_cases.json` | 12 golden cases for the LangGraph pipeline eval |
| `golden_qa.json` | 20 coverage Q&A pairs for `coverage_qa_eval` |
| `hallucination_golden.json` | Hallucination trap cases for `hallucination_eval` |

Each `agent_pipeline_cases.json` record has:
- `id`, `question`
- `expected_intent`, `expected_tool`
- `required_phrases`, `forbidden_phrases`
- `expected_grounded`, `expected_escalate`
- `notes`

Keep datasets in version control so prompt/graph changes get reviewed.

## Add a new task

Drop a new file in `eval/tasks/` that exports a `@task` function. Use the
existing tasks as templates.
