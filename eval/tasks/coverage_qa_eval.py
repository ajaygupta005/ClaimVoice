"""Coverage Q&A eval against 20 golden pairs."""
import json
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import model_graded_qa
from inspect_ai.solver import generate, system_message

DATASET = Path(__file__).parent.parent / "datasets" / "golden_qa.json"

SYSTEM = """You are ClaimVoice, a helpful insurance assistant. Answer member
questions about coverage, cost, and providers using ONLY information in the
member's context. Be brief and conversational (this is a phone call). If
the context lacks information, say so plainly."""


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
        solver=[system_message(SYSTEM), generate()],
        scorer=model_graded_qa(),
    )
