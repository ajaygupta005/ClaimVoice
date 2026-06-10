"""Coverage Q&A eval against golden pairs."""
import json
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import model_graded_qa
from inspect_ai.solver import generate

DATASET = Path(__file__).parent.parent / "datasets" / "golden_qa.json"


def load_samples():
    records = json.loads(DATASET.read_text(encoding="utf-8"))
    return [
        Sample(
            input=f"Member context: {r['member_context']}\n\nQuestion: {r['question']}",
            target=r["expected_answer"],
        )
        for r in records
    ]


@task
def coverage_qa_eval():
    return Task(
        dataset=load_samples(),
        solver=generate(),
        scorer=model_graded_qa(),
    )
