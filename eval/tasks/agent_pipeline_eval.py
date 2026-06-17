"""
Component 34 — Agent pipeline evaluation harness.

Evaluates the LangGraph mock runtime end-to-end against a deterministic
golden dataset.  No Anthropic API key or database is required for the
deterministic scorer.  An optional model judge can be enabled by setting
ANTHROPIC_API_KEY — it runs as an advisory layer on top of the required
deterministic gate.

Run:
    inspect eval eval/tasks/agent_pipeline_eval.py                  # deterministic only
    inspect eval eval/tasks/agent_pipeline_eval.py --model claude-sonnet-4-6  # + LLM judge

The task also imports cleanly for unit tests:
    from eval.tasks.agent_pipeline_eval import run_case, score_case, load_cases
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── path setup: make voice-agent importable without install ──────────────────
_VA_SRC = (
    Path(__file__).resolve().parent.parent.parent
    / "services" / "voice-agent" / "src"
)
if str(_VA_SRC) not in sys.path:
    sys.path.insert(0, str(_VA_SRC))

from voice_agent.schemas.transcript import FinalTranscriptEvent  # noqa: E402
from voice_agent.services.answer_orchestrator import orchestrate  # noqa: E402

DATASET_PATH = Path(__file__).parent.parent / "datasets" / "agent_pipeline_cases.json"

# ── types ─────────────────────────────────────────────────────────────────────

@dataclass
class PipelineResult:
    """Normalised output of one pipeline run."""
    answer: str
    intent: str
    tool: str
    grounded: bool
    escalate: bool
    tool_trace: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ScoreResult:
    """Outcome of the deterministic scorer for one case."""
    passed: bool
    failures: list[str] = field(default_factory=list)
    case_id: str = ""
    question: str = ""
    expected_intent: str = ""
    actual_intent: str = ""
    expected_tool: str = ""
    actual_tool: str = ""
    answer: str = ""


# ── dataset loader ────────────────────────────────────────────────────────────

def load_cases() -> list[dict[str, Any]]:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


# ── pipeline adapter ──────────────────────────────────────────────────────────

def run_case(question: str, call_sid: str = "CA-eval", stream_sid: str = "SM-eval") -> PipelineResult:
    """Convert a question into a FinalTranscriptEvent, run orchestrate(), normalise output."""
    transcript = FinalTranscriptEvent(
        callSid=call_sid,
        streamSid=stream_sid,
        text=question,
        confidence=1.0,
        duration_ms=None,
    )
    ev = orchestrate(transcript)
    tool = ev.tool_trace[0].tool if ev.tool_trace else ""
    escalate = tool == "escalate_to_human"
    return PipelineResult(
        answer=ev.text,
        intent=ev.intent,
        tool=tool,
        grounded=ev.grounded,
        escalate=escalate,
        tool_trace=[t.model_dump() for t in ev.tool_trace],
    )


# ── deterministic scorer ──────────────────────────────────────────────────────

def score_case(case: dict[str, Any], result: PipelineResult) -> ScoreResult:
    """
    Apply all deterministic checks for one case.  Returns a ScoreResult with
    a list of human-readable failure reasons.
    """
    failures: list[str] = []

    if result.intent != case["expected_intent"]:
        failures.append(
            f"intent: expected={case['expected_intent']!r} actual={result.intent!r}"
        )

    if result.tool != case["expected_tool"]:
        failures.append(
            f"tool: expected={case['expected_tool']!r} actual={result.tool!r}"
        )

    answer_lower = result.answer.lower()
    for phrase in case.get("required_phrases", []):
        if phrase.lower() not in answer_lower:
            failures.append(f"missing required phrase: {phrase!r}")

    for phrase in case.get("forbidden_phrases", []):
        if phrase.lower() in answer_lower:
            failures.append(f"forbidden phrase present: {phrase!r}")

    if result.grounded != case["expected_grounded"]:
        failures.append(
            f"grounded: expected={case['expected_grounded']} actual={result.grounded}"
        )

    if result.escalate != case["expected_escalate"]:
        failures.append(
            f"escalate: expected={case['expected_escalate']} actual={result.escalate}"
        )

    return ScoreResult(
        passed=len(failures) == 0,
        failures=failures,
        case_id=case.get("id", ""),
        question=case.get("question", ""),
        expected_intent=case.get("expected_intent", ""),
        actual_intent=result.intent,
        expected_tool=case.get("expected_tool", ""),
        actual_tool=result.tool,
        answer=result.answer,
    )


# ── Inspect AI task ───────────────────────────────────────────────────────────

def _build_inspect_task():
    """
    Returns an Inspect AI Task.  Called lazily so the module still imports
    cleanly in environments where inspect-ai is not installed (e.g. unit tests
    that only exercise run_case / score_case).
    """
    from inspect_ai import Task, task as inspect_task  # noqa: F401
    from inspect_ai.dataset import Sample
    from inspect_ai.scorer import Score, Scorer, scorer, accuracy
    from inspect_ai.solver import Solver, TaskState, Generate, solver

    cases = load_cases()

    # ── build samples ─────────────────────────────────────────────────────────
    samples = [
        Sample(
            input=c["question"],
            target=c["expected_intent"],
            metadata=c,
        )
        for c in cases
    ]

    # ── pipeline solver — runs the actual LangGraph agent ────────────────────
    @solver
    def pipeline_solver() -> Solver:
        async def solve(state: TaskState, generate: Generate) -> TaskState:
            result = run_case(state.input_text)
            # Attach full result to metadata so scorer and LLM judge can read it
            state.metadata["_result"] = {
                "answer": result.answer,
                "intent": result.intent,
                "tool": result.tool,
                "grounded": result.grounded,
                "escalate": result.escalate,
                "tool_trace": result.tool_trace,
            }
            # Set model output so Inspect AI logs the answer text
            from inspect_ai.model import ChatMessageAssistant
            state.messages.append(ChatMessageAssistant(content=result.answer))
            return state
        return solve

    # ── deterministic scorer ──────────────────────────────────────────────────
    @scorer(metrics=[accuracy()])
    def deterministic_scorer() -> Scorer:
        async def score(state: TaskState, target) -> Score:
            case = state.metadata
            raw = state.metadata.get("_result", {})
            result = PipelineResult(
                answer=raw.get("answer", ""),
                intent=raw.get("intent", ""),
                tool=raw.get("tool", ""),
                grounded=raw.get("grounded", False),
                escalate=raw.get("escalate", False),
                tool_trace=raw.get("tool_trace", []),
            )
            sr = score_case(case, result)
            value = 1.0 if sr.passed else 0.0
            explanation = (
                "All checks passed."
                if sr.passed
                else "Failures:\n" + "\n".join(f"  • {f}" for f in sr.failures)
            )
            return Score(
                value=value,
                answer=result.answer,
                explanation=explanation,
                metadata={
                    "case_id": sr.case_id,
                    "expected_intent": sr.expected_intent,
                    "actual_intent": sr.actual_intent,
                    "expected_tool": sr.expected_tool,
                    "actual_tool": sr.actual_tool,
                },
            )
        return score

    # ── optional LLM judge (advisory only) ───────────────────────────────────
    use_llm_judge = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if use_llm_judge:
        from inspect_ai.scorer import model_graded_qa
        judge_instructions = (
            "The agent answered a member's health-insurance phone query. "
            "Judge whether the answer is factually sensible, member-friendly, "
            "and does not invent specific coverage or cost facts. "
            "Score GRADE: C if the answer is acceptable, GRADE: I if it is "
            "misleading or invents facts."
        )
        scorers = [deterministic_scorer(), model_graded_qa(instructions=judge_instructions)]
    else:
        scorers = [deterministic_scorer()]

    return Task(
        dataset=samples,
        solver=[pipeline_solver()],
        scorer=scorers,
    )


# Inspect AI discovers the @task decorator at import time.
try:
    from inspect_ai import task as _task_decorator

    @_task_decorator
    def agent_pipeline_eval():
        return _build_inspect_task()

except ImportError:
    # Running without inspect-ai installed (unit-test context) — skip registration.
    pass
