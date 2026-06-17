"""Node: hallucination_guard — verify answer claims against tool result facts."""

from __future__ import annotations

import re

from voice_agent.graph.agent_state import AgentState


def hallucination_guard(state: AgentState) -> AgentState:
    """
    Checks that any dollar amount in the answer text also appears in the tool
    result.  Escalation answers always pass — they contain no factual claims.
    """
    intent = state.get("intent", "escalate")
    answer = state.get("answer_text", "")
    tool_result = state.get("tool_result", "")

    if intent == "escalate":
        return {**state, "grounded": False, "guard_reason": "escalated — no factual claims"}

    answer_amounts = set(re.findall(r"\$[\d,]+", answer))
    result_amounts = set(re.findall(r"\$[\d,]+", tool_result))
    hallucinated = answer_amounts - result_amounts

    if hallucinated:
        return {
            **state,
            "grounded": False,
            "guard_reason": f"ungrounded amounts: {hallucinated}",
        }

    return {
        **state,
        "grounded": True,
        "guard_reason": "all claims grounded in tool result",
    }
