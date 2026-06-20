"""Node: hallucination_guard — verify answer claims against the tool's grounding facts.

In ``tool_mode="http"`` this calls WS-4 POST /fact_check; otherwise it runs the same
matcher in-process. Escalation answers always pass (no factual claims).
"""

from __future__ import annotations

from voice_agent.core.config import settings
from voice_agent.graph.agent_state import AgentState
from voice_agent.guards.hallucination import fact_check


def hallucination_guard(state: AgentState) -> AgentState:
    intent = state.get("intent", "escalate")
    if intent == "escalate":
        return {**state, "grounded": False, "guard_reason": "escalated — no factual claims"}

    answer = state.get("answer_text", "")
    facts = state.get("tool_facts") or [state.get("tool_result", "")]

    grounded, reason = fact_check(
        answer, facts, mode=settings.tool_mode, base_url=settings.eligibility_base_url
    )
    return {**state, "grounded": grounded, "guard_reason": reason}
