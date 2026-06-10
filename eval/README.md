# Eval suite

Inspect AI tasks that score the agent against golden Q&A pairs.

## Run

```
just eval
```

Or directly:

```
ANTHROPIC_API_KEY=sk-... inspect eval eval/tasks/coverage_qa_eval.py
```

## Add a new task

Drop a new file in `eval/tasks/`. Decorate it with `@task`. Use existing
ones as templates.

## Datasets

Golden Q&A pairs live in `eval/datasets/`. Each pair has a member_context,
question, and expected_answer. Keep these in version control so changes get
reviewed.
