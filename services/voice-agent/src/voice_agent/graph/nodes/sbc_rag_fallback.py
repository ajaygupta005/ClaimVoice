"""Node: sbc_rag_fallback — retrieve SBC chunks as grounding evidence.

Runs after call_tool for coverage and formulary intents. Structured tool results
remain primary; this node adds RAG evidence when available.

In mock mode (tool_mode != "http") the node is a no-op and writes explicit
"not applicable" metadata so callers never assume RAG was tried.

Member plan_id lookup: the eligibility service returns a `planId` in successful
coverage/formulary responses. In mock mode or when the plan_id is absent the
client skips the RAG call and records `missing_plan_id`.
"""

from __future__ import annotations

from voice_agent.core.config import settings
from voice_agent.graph.agent_state import AgentState
from voice_agent.lib.logger import logger
from voice_agent.tools.sbc_rag_client import (
    RagResult,
    _NOT_ATTEMPTED,
    retrieve,
    should_attempt_rag,
)


def _plan_id_from_tool_args(state: AgentState) -> str:
    """Extract plan_id from tool_args or state, or return empty string."""
    # Real eligibility coverage/formulary endpoints return planId in the fact payload.
    # We store it in state.plan_id when available.
    return state.get("plan_id") or ""


def _apply(state: AgentState, rag: RagResult) -> AgentState:
    chunks_as_dicts = [
        {
            "chunk_text": c.chunk_text,
            "section_name": c.section_name,
            "source_file": c.source_file,
            "distance": c.distance,
        }
        for c in rag.chunks
    ]
    return {
        **state,
        "rag_attempted": rag.attempted,
        "rag_available": rag.available,
        "rag_chunks_count": rag.chunks_count,
        "rag_fallback_reason": rag.fallback_reason,
        "rag_source": rag.source,
        "rag_chunks": chunks_as_dicts,
    }


def sbc_rag_fallback(state: AgentState) -> AgentState:
    intent = state.get("intent", "")
    tool_ok = bool(state.get("tool_facts") or state.get("tool_result"))

    # Only run RAG in http mode — mock mode has no real eligibility service.
    if settings.tool_mode != "http":
        return _apply(state, RagResult(
            attempted=False,
            fallback_reason="rag_mock_mode",
        ))

    if not should_attempt_rag(intent, tool_ok):
        return _apply(state, _NOT_ATTEMPTED)

    plan_id = _plan_id_from_tool_args(state)
    question = state.get("question", "")

    logger.info(
        "sbc_rag.attempt",
        intent=intent,
        plan_id=plan_id or "(none)",
        question=question[:80],
    )

    rag = retrieve(
        plan_id=plan_id,
        query=question,
        base_url=settings.eligibility_base_url,
        top_k=3,
        timeout=5.0,
    )

    logger.info(
        "sbc_rag.result",
        attempted=rag.attempted,
        available=rag.available,
        chunks=rag.chunks_count,
        fallback_reason=rag.fallback_reason,
    )

    return _apply(state, rag)
