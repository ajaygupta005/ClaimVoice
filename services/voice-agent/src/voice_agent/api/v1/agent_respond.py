"""
POST /api/v1/agent/respond

HTTP entry point for the web UI bridge (Component 36).
Accepts a text question, runs the LangGraph pipeline via orchestrate(),
and returns a structured JSON response the browser can consume directly.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from loguru import logger

from voice_agent.core.config import settings
from voice_agent.schemas.agent_respond import (
    AgentRespondRequest,
    AgentRespondResponse,
    ToolTraceItem,
)
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


@router.post("/agent/respond", response_model=AgentRespondResponse)
async def agent_respond(req: AgentRespondRequest) -> AgentRespondResponse:
    call_sid, stream_sid = _demo_sids(req.source)
    session_id = req.sessionId or call_sid

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
        )
        for t in ev.tool_trace
    ]

    # guard_reason comes from AgentState; not in AnswerFinalEvent — re-derive it
    guard_reason = "escalated — no factual claims" if not ev.grounded and ev.intent == "escalate" \
        else ("all claims grounded in tool result" if ev.grounded else "ungrounded claims detected")

    logger.info(
        "agent_respond",
        call_sid=call_sid,
        intent=ev.intent,
        grounded=ev.grounded,
        composer=composer_mode,
    )

    return AgentRespondResponse(
        question=req.question,
        answer=ev.text,
        intent=ev.intent,
        grounded=ev.grounded,
        guard_reason=guard_reason,
        tool_trace=tool_trace,
        composer_mode=composer_mode,
        backend_statuses=_backend_statuses(composer_mode, ev.grounded),
    )
