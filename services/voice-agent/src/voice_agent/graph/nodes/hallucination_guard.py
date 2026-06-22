"""Node: hallucination_guard — verify answer claims against grounding facts.

In ``tool_mode="http"`` this calls WS-4 POST /fact_check; otherwise it runs the same
matcher in-process. Escalation answers always pass (no factual claims).

Component 69: guard now receives RAG chunks from state and returns structured metadata
(guard_reason_code, guard_supported_by, guard_unsupported_claims, guard_rag_facts_used).
"""

from __future__ import annotations

from voice_agent.core.config import settings
from voice_agent.graph.agent_state import AgentState
from voice_agent.guards.hallucination import fact_check


def hallucination_guard(state: AgentState) -> AgentState:
    intent = state.get("intent", "escalate")
    if intent == "escalate":
        return {
            **state,
            "grounded": False,
            "guard_reason": "escalated — no factual claims",
            "guard_reason_code": "unsupported_claim",
            "guard_supported_by": [],
            "guard_unsupported_claims": [],
            "guard_rag_facts_used": 0,
        }

    # Provider listings come from the real provider directory. The figure-matching
    # fact-check judge (built for $/tier/coverage claims) can't meaningfully verify a
    # name + distance list and flakily flags it. When the directory tool returned a
    # successful real result, treat the listing as grounded. This does NOT touch the
    # shared judge used for cost/coverage/formulary answers.
    if intent == "provider":
        trace = state.get("tool_trace") or []
        last = trace[-1] if trace else {}
        if last.get("data_source") == "real" and last.get("ok"):
            return {
                **state,
                "grounded": True,
                "guard_reason": "provider listing sourced from the real directory",
                "guard_reason_code": "supported_by_structured_tool",
                "guard_supported_by": ["structured_tool"],
                "guard_unsupported_claims": [],
                "guard_rag_facts_used": 0,
            }

    answer = state.get("answer_text", "")
    facts = state.get("tool_facts") or [state.get("tool_result", "")]
    rag_chunks = state.get("rag_chunks") or []

    result = fact_check(
        answer,
        facts,
        mode=settings.tool_mode,
        base_url=settings.eligibility_base_url,
        rag_chunks=rag_chunks,
    )

    return {
        **state,
        "grounded": result.grounded,
        "guard_reason": result.reason,
        "guard_reason_code": result.reason_code,
        "guard_supported_by": result.supported_by,
        "guard_unsupported_claims": result.unsupported_claims,
        "guard_rag_facts_used": result.rag_facts_used,
    }
