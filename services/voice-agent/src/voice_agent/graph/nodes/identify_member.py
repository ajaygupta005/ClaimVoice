"""Node: identify_member — preserve the threaded member id and mark verified.

The real member id is threaded in by the HTTP/telephony layers (defaulting to the mock
member for bare callers). In tool_mode=http a future step can verify against WS-4; here we
keep the graph deterministic and always mark verified.
"""

from __future__ import annotations

from voice_agent.graph.agent_state import AgentState


def identify_member(state: AgentState) -> AgentState:
    member_id = state.get("member_id") or "MOCK-MEMBER-001"
    return {
        **state,
        "member_id": member_id,
        "member_verified": True,
    }
