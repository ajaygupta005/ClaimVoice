"""
Turn-level observability for the WS-7 voice agent (Component 65).

Usage in the eval runner:

    with TurnTracer(turn_id="abc", scenario_id="mri-coverage") as t:
        ev = orchestrate(transcript)
        t.set_result(ev)

``TurnTrace`` is the immutable record produced at the end of each turn.
``TurnTracer`` is the context manager that measures timings.
``LangfuseHook`` emits a trace when LANGFUSE_* env vars are present.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class StageTimingRecord:
    name: str
    status: str          # "ok" | "error" | "escalated" | "demo"
    duration_ms: int
    detail: str = ""


@dataclass
class ToolCallRecord:
    tool: str
    args: dict[str, Any]
    result_summary: str  # first 200 chars
    ok: bool
    data_source: str     # "real" | "demo" | "error"
    error_code: str = ""
    member_source: str = ""


@dataclass
class GuardRecord:
    passed: bool
    reason: str


@dataclass
class TurnTrace:
    """Immutable observability record for one agent turn."""
    turn_id: str
    scenario_id: str
    question: str
    intent: str
    grounded: bool
    total_ms: int
    stages: list[StageTimingRecord]
    tools: list[ToolCallRecord]
    guard: GuardRecord
    answer_snippet: str  # first 200 chars
    tool_mode: str       # "mock" | "http"
    composer_mode: str   # "mock" | "claude"
    member_source: str   # "provided" | "demo" | "missing"
    error: str = ""      # non-empty if the pipeline itself failed

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)


# ── Tracer ────────────────────────────────────────────────────────────────────

class TurnTracer:
    """
    Context manager that records a single agent turn.

    On exit it builds a ``TurnTrace`` and optionally emits to Langfuse.
    """

    def __init__(
        self,
        *,
        turn_id: str | None = None,
        scenario_id: str = "",
        question: str = "",
        tool_mode: str = "mock",
        composer_mode: str = "mock",
    ) -> None:
        self.turn_id = turn_id or uuid.uuid4().hex
        self.scenario_id = scenario_id
        self.question = question
        self.tool_mode = tool_mode
        self.composer_mode = composer_mode

        self._start = 0.0
        self._result: Any = None   # AnswerFinalEvent
        self._stage_records: list[StageTimingRecord] = []
        self._error = ""
        self.trace: TurnTrace | None = None

    def __enter__(self) -> "TurnTracer":
        self._start = time.monotonic()
        return self

    def set_result(self, ev: Any) -> None:
        """Call once with the AnswerFinalEvent returned by orchestrate()."""
        self._result = ev

    def set_error(self, msg: str) -> None:
        self._error = msg

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        total_ms = int((time.monotonic() - self._start) * 1000)
        ev = self._result

        if ev is None or exc_type is not None:
            self.trace = TurnTrace(
                turn_id=self.turn_id,
                scenario_id=self.scenario_id,
                question=self.question,
                intent="",
                grounded=False,
                total_ms=total_ms,
                stages=[],
                tools=[],
                guard=GuardRecord(passed=False, reason="pipeline_error"),
                answer_snippet="",
                tool_mode=self.tool_mode,
                composer_mode=self.composer_mode,
                member_source="",
                error=self._error or (str(exc_val) if exc_val else "unknown_error"),
            )
            return

        tools = [
            ToolCallRecord(
                tool=t.tool,
                args=t.args,
                result_summary=t.result[:200],
                ok=t.ok,
                data_source=getattr(t, "data_source", "demo"),
                error_code=getattr(t, "error_code", ""),
                member_source=getattr(t, "member_source", ""),
            )
            for t in (ev.tool_trace or [])
        ]

        intent = ev.intent
        grounded = ev.grounded

        member_source = next(
            (t.member_source for t in reversed(tools) if t.member_source),
            "demo",
        )

        # Synthetic stage records (timing not individually tracked in mock mode)
        tool_status = (
            "escalated" if intent == "escalate"
            else ("error" if tools and tools[0].data_source == "error" else
                  ("demo" if tools and tools[0].data_source == "demo" else "ok"))
        )
        stages = [
            StageTimingRecord(name="identify",   status="ok",         duration_ms=0, detail=f"member_source:{member_source}"),
            StageTimingRecord(name="understand", status="ok",         duration_ms=0, detail=f"intent:{intent}"),
            StageTimingRecord(name="tool",       status=tool_status,  duration_ms=0),
            StageTimingRecord(name="guard",      status=("ok" if grounded else "error"), duration_ms=0),
            StageTimingRecord(name="respond",    status="ok",         duration_ms=total_ms),
        ]

        guard_reason = (
            "escalated — no factual claims" if intent == "escalate"
            else ("all claims grounded in tool result" if grounded else "ungrounded claims detected")
        )

        self.trace = TurnTrace(
            turn_id=self.turn_id,
            scenario_id=self.scenario_id,
            question=self.question,
            intent=intent,
            grounded=grounded,
            total_ms=total_ms,
            stages=stages,
            tools=tools,
            guard=GuardRecord(passed=grounded, reason=guard_reason),
            answer_snippet=ev.text[:200],
            tool_mode=self.tool_mode,
            composer_mode=self.composer_mode,
            member_source=member_source,
            error=self._error,
        )

        _emit_langfuse(self.trace)


# ── Langfuse hook (optional, no-op when not configured) ──────────────────────

def _emit_langfuse(trace: TurnTrace) -> None:
    """
    Emit a Langfuse trace when LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY are set.
    Silently skips if langfuse is not installed or keys are absent.
    No PHI is emitted — question text is included as member input, which
    callers should ensure is synthetic in CI.
    """
    import os
    if not (os.environ.get("LANGFUSE_SECRET_KEY") and os.environ.get("LANGFUSE_PUBLIC_KEY")):
        return

    try:
        from langfuse import Langfuse  # type: ignore[import-untyped]
    except ImportError:
        return

    try:
        lf = Langfuse()
        t = lf.trace(
            id=trace.turn_id,
            name=f"eval:{trace.scenario_id}",
            input={"question": trace.question},
            output={"answer": trace.answer_snippet},
            metadata={
                "intent": trace.intent,
                "grounded": trace.grounded,
                "tool_mode": trace.tool_mode,
                "composer_mode": trace.composer_mode,
                "total_ms": trace.total_ms,
                "guard": {"passed": trace.guard.passed, "reason": trace.guard.reason},
            },
        )
        for tool in trace.tools:
            t.span(
                name=f"tool:{tool.tool}",
                input={"args": tool.args},
                output={"result": tool.result_summary, "ok": tool.ok},
                metadata={"data_source": tool.data_source, "error_code": tool.error_code},
            )
        lf.flush()
    except Exception:
        pass  # Langfuse is optional — never crash the eval runner
