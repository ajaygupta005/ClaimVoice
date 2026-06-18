"""
End-to-end voice evaluation.

Runs the full voice turn over the agent-pipeline golden cases:
    question (final transcript) -> orchestrate (LangGraph) -> answer -> TTS audio

and checks both the orchestration result (intent / grounded) and that the voice loop
produces final TTS audio. It respects the voice-agent run modes via env:
- TOOL_MODE=mock (default): fully deterministic, no DB/services/keys (CI gate).
- TOOL_MODE=http: tools + guard call live WS-4/WS-5 (set ELIGIBILITY_BASE_URL /
  PROVIDERS_BASE_URL and have those services + the seeded DB up).

Run:
    inspect eval eval/tasks/e2e_voice_eval.py

Importable for unit tests:
    from eval.tasks.e2e_voice_eval import run_voice_turn, score_voice_turn, load_cases
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_VA_SRC = Path(__file__).resolve().parent.parent.parent / "services" / "voice-agent" / "src"
if str(_VA_SRC) not in sys.path:
    sys.path.insert(0, str(_VA_SRC))

from voice_agent.schemas.transcript import FinalTranscriptEvent  # noqa: E402
from voice_agent.services.answer_orchestrator import orchestrate  # noqa: E402
from voice_agent.streaming.factory import build_tts  # noqa: E402

DATASET_PATH = Path(__file__).parent.parent / "datasets" / "agent_pipeline_cases.json"


@dataclass
class VoiceTurn:
    answer: str
    intent: str
    grounded: bool
    audio_chunks: int
    has_final_audio: bool


@dataclass
class VoiceScore:
    passed: bool
    case_id: str = ""
    failures: list[str] = field(default_factory=list)


def load_cases() -> list[dict[str, Any]]:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def run_voice_turn(question: str, member_id: str = "CVX-0042-MT") -> VoiceTurn:
    transcript = FinalTranscriptEvent(
        callSid="CA-e2e", streamSid="SM-e2e", text=question, confidence=1.0, duration_ms=None
    )
    ev = orchestrate(transcript, member_id=member_id)
    audio = build_tts().synthesize(ev.text, "CA-e2e", "SM-e2e")
    chunks = [e for e in audio if getattr(e, "pcm24k", None)]
    return VoiceTurn(
        answer=ev.text,
        intent=ev.intent,
        grounded=bool(ev.grounded),
        audio_chunks=len(chunks),
        has_final_audio=any(getattr(e, "isFinal", False) for e in audio),
    )


def score_voice_turn(case: dict[str, Any], turn: VoiceTurn) -> VoiceScore:
    failures: list[str] = []
    if turn.intent != case["expected_intent"]:
        failures.append(f"intent: expected={case['expected_intent']!r} actual={turn.intent!r}")
    if turn.grounded != case["expected_grounded"]:
        failures.append(f"grounded: expected={case['expected_grounded']} actual={turn.grounded}")
    if not turn.answer.strip():
        failures.append("empty answer")
    if turn.audio_chunks < 1:
        failures.append("no TTS audio produced")
    if not turn.has_final_audio:
        failures.append("no final TTS chunk")
    return VoiceScore(passed=not failures, case_id=case.get("id", ""), failures=failures)


def _build_inspect_task():
    from inspect_ai import Task
    from inspect_ai.dataset import Sample
    from inspect_ai.model import ChatMessageAssistant
    from inspect_ai.scorer import Score, Scorer, accuracy, scorer
    from inspect_ai.solver import Generate, Solver, TaskState, solver

    cases = load_cases()
    samples = [Sample(input=c["question"], target=c["expected_intent"], metadata=c) for c in cases]

    @solver
    def voice_solver() -> Solver:
        async def solve(state: TaskState, generate: Generate) -> TaskState:
            turn = run_voice_turn(state.input_text)
            state.metadata["_turn"] = turn.__dict__
            state.messages.append(ChatMessageAssistant(content=turn.answer))
            return state

        return solve

    @scorer(metrics=[accuracy()])
    def voice_scorer() -> Scorer:
        async def score(state: TaskState, target) -> Score:
            raw = state.metadata.get("_turn", {})
            turn = VoiceTurn(**raw)
            sr = score_voice_turn(state.metadata, turn)
            return Score(
                value=1.0 if sr.passed else 0.0,
                answer=turn.answer,
                explanation="ok" if sr.passed else "; ".join(sr.failures),
                metadata={"case_id": sr.case_id},
            )

        return score

    return Task(dataset=samples, solver=[voice_solver()], scorer=[voice_scorer()])


try:
    from inspect_ai import task as _task

    @_task
    def e2e_voice_eval():
        return _build_inspect_task()

except ImportError:
    pass
