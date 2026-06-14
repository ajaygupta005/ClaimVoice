"""Node: identify_member — mock member verification."""

from __future__ import annotations

from voice_agent.graph.agent_state import AgentState


def identify_member(state: AgentState) -> AgentState:
    """
    In production this would verify DOB + ZIP against the eligibility service.
    Here we always succeed so the graph stays deterministic.
    """
    return {
        **state,
        "member_id": "MOCK-MEMBER-001",
        "member_verified": True,
    }
