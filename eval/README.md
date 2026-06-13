# Eval suite

Inspect AI tasks that score the agent.

## Tasks

| Task | What it measures |
| --- | --- |
| `coverage_qa_eval` | Accuracy on 20 golden coverage Q&A pairs |
| `hallucination_eval` | Whether the agent ever states a coverage fact not in the plan context |

## Run

```bash
just eval                                          # all tasks
inspect eval eval/tasks/coverage_qa_eval.py        # one task
inspect eval eval/tasks/hallucination_eval.py
```

Set `ANTHROPIC_API_KEY` first.

## Add a new task

Drop a new file in `eval/tasks/` that exports a `@task` function. Use the
existing tasks as templates.

## Datasets

Golden pairs are in `eval/datasets/`. Each pair has fields:
- `member_context` or `plan_context`
- `question`
- `expected_answer` or `truth_label`

Keep these in version control so prompt changes get reviewed.
