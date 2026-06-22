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
