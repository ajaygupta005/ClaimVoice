"""
Grounded answer orchestrator (Component 26, updated C32).

Delegates to the LangGraph mock runtime (graph/state_machine.py) while
preserving the original synchronous orchestrate() signature so the
WebSocket layer does not need to change.
"""

from __future__ import annotations

from voice_agent.graph.state_machine import run_agent_graph
from voice_agent.schemas.answer import AnswerFinalEvent, ToolTrace
from voice_agent.schemas.transcript import FinalTranscriptEvent


def orchestrate(
    transcript: FinalTranscriptEvent,
    member_id: str = "MOCK-MEMBER-001",
    history: list[dict] | None = None,
) -> AnswerFinalEvent:
    """
    Run the LangGraph pipeline and return an AnswerFinalEvent ready for TTS.
    ``member_id`` and ``history`` are threaded through by the HTTP/telephony layers;
    bare callers keep the deterministic defaults.
    """
    state = run_agent_graph(
        question=transcript.text,
        call_sid=transcript.callSid,
        stream_sid=transcript.streamSid,
        member_id=member_id,
        history=history,
    )

    raw_traces = state.get("tool_trace") or []
    tool_trace = [
        ToolTrace(
            tool=t["tool"],
            args=t.get("args", {}),
            result=t.get("result", ""),
            ok=bool(t.get("ok", False)),
            data_source=t.get("data_source", "demo"),
            error_code=t.get("error_code", ""),
            member_source=t.get("member_source", ""),
        )
        for t in raw_traces
    ]

    return AnswerFinalEvent(
        callSid=transcript.callSid,
        streamSid=transcript.streamSid,
        intent=state.get("intent", "escalate"),
        text=state.get("answer_text", ""),
        grounded=bool(state.get("grounded", False)),
        tool_trace=tool_trace,
    )
