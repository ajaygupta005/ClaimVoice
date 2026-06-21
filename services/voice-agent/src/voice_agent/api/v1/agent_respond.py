"""
POST /api/v1/agent/respond

HTTP entry point for the web UI bridge (Component 36, updated C63).
Accepts a text question, runs the LangGraph pipeline via orchestrate(),
and returns a structured JSON response including the pipeline event contract.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from loguru import logger

from voice_agent.core.config import settings
from voice_agent.schemas.agent_respond import (
    AgentRespondRequest,
    AgentRespondResponse,
    PipelineAnswer,
    PipelineGuard,
    PipelineStage,
    PipelineSummary,
    PipelineToolCall,
    ToolTraceItem,
)
from voice_agent.schemas.answer import AnswerFinalEvent
from voice_agent.schemas.transcript import FinalTranscriptEvent
from voice_agent.services.answer_orchestrator import orchestrate
from voice_agent.services.session_memory import append_turn, get_history

router = APIRouter()


def _demo_sids(source: str) -> tuple[str, str]:
    uid = uuid.uuid4().hex[:8]
    return f"CA-web-{source}-{uid}", f"SM-web-{source}-{uid}"


def _backend_statuses(composer_mode: str, grounded: bool) -> list[dict[str, str]]:
    return [
        {
            "label": "Voice Agent API",
            "detail": "localhost:8004",
            "status": "connected",
        },
        {
            "label": "STT",
            "detail": "text input (demo)",
            "status": "demo",
        },
        {
            "label": "TTS",
            "detail": "browser (demo)",
            "status": "demo",
        },
        {
            "label": "Hallucination guard",
            "detail": "passed" if grounded else "flagged",
            "status": "connected" if grounded else "degraded",
        },
        {
            "label": "Claude",
            "detail": composer_mode,
            "status": "connected" if composer_mode == "claude" else "demo",
        },
    ]


def _build_pipeline(
    ev: AnswerFinalEvent,
    tool_trace: list[ToolTraceItem],
    composer_mode: str,
    member_source: str,
    tool_mode: str,
    guard_reason: str,
    turn_id: str,
) -> PipelineSummary:
    intent = ev.intent
    grounded = ev.grounded

    # Determine tool stage status from the first tool trace entry.
    if intent == "escalate":
        tool_status = "escalated"
    elif tool_trace:
        first = tool_trace[0]
        if first.data_source == "error":
            tool_status = "error"
        elif first.data_source == "demo":
            tool_status = "demo"
        else:
            tool_status = "ok"
    else:
        tool_status = "ok"

    guard_status = (
        "escalated" if intent == "escalate"
        else ("ok" if grounded else "error")
    )

    stages = [
        PipelineStage(name="identify",   status="ok", detail=f"member_source: {member_source}"),
        PipelineStage(name="understand", status="ok", detail=f"intent: {intent}"),
        PipelineStage(name="tool",       status=tool_status),
        PipelineStage(name="guard",      status=guard_status, detail=guard_reason),
        PipelineStage(name="respond",    status="ok"),
    ]

    tools = [
        PipelineToolCall(
            tool=t.tool,
            data_source=t.data_source,
            error_code=t.error_code,
            result_summary=t.result[:120],
            ok=t.ok,
        )
        for t in tool_trace
    ]

    # Answer source
    if intent == "escalate":
        answer_source = "escalated"
    elif tool_trace and not tool_trace[0].ok:
        answer_source = "tool_error"
    elif composer_mode == "claude":
        answer_source = "claude"
    else:
        answer_source = "mock"

    return PipelineSummary(
        turn_id=turn_id,
        intent=intent,
        member_source=member_source,
        tool_mode=tool_mode,
        stages=stages,
        tools=tools,
        guard=PipelineGuard(passed=grounded, reason=guard_reason),
        answer=PipelineAnswer(source=answer_source, grounded=grounded),
    )


@router.post("/agent/respond", response_model=AgentRespondResponse)
async def agent_respond(req: AgentRespondRequest) -> AgentRespondResponse:
    call_sid, stream_sid = _demo_sids(req.source)
    session_id = req.sessionId or call_sid
    turn_id = uuid.uuid4().hex

    transcript = FinalTranscriptEvent(
        callSid=call_sid,
        streamSid=stream_sid,
        text=req.question,
        confidence=1.0,
        duration_ms=None,
    )

    try:
        ev = orchestrate(transcript, member_id=req.memberId, history=get_history(session_id))
    except Exception as exc:
        logger.error(f"agent_respond orchestrate failed: {exc!r}")
        raise HTTPException(status_code=500, detail="Pipeline error") from exc

    append_turn(session_id, req.question, ev.text)

    composer_mode = settings.voice_agent_answer_mode
    tool_trace = [
        ToolTraceItem(
            tool=t.tool,
            args=t.args,
            result=t.result,
            ok=t.ok,
            data_source=getattr(t, "data_source", "demo"),
            error_code=getattr(t, "error_code", ""),
            member_source=getattr(t, "member_source", ""),
        )
        for t in ev.tool_trace
    ]

    guard_reason = "escalated — no factual claims" if not ev.grounded and ev.intent == "escalate" \
        else ("all claims grounded in tool result" if ev.grounded else "ungrounded claims detected")

    member_source = next(
        (t.member_source for t in reversed(tool_trace) if t.member_source),
        "demo" if settings.demo_mode else "missing",
    )

    pipeline = _build_pipeline(
        ev=ev,
        tool_trace=tool_trace,
        composer_mode=composer_mode,
        member_source=member_source,
        tool_mode=settings.tool_mode,
        guard_reason=guard_reason,
        turn_id=turn_id,
    )

    logger.info(
        "agent_respond",
        call_sid=call_sid,
        intent=ev.intent,
        grounded=ev.grounded,
        composer=composer_mode,
        tool_mode=settings.tool_mode,
        member_source=member_source,
        turn_id=turn_id,
    )

    return AgentRespondResponse(
        question=req.question,
        answer=ev.text,
        intent=ev.intent,
        grounded=ev.grounded,
        guard_reason=guard_reason,
        tool_trace=tool_trace,
        composer_mode=composer_mode,
        tool_mode=settings.tool_mode,
        member_source=member_source,
        backend_statuses=_backend_statuses(composer_mode, ev.grounded),
        pipeline=pipeline,
    )
