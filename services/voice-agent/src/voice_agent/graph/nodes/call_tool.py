"""Node: call_tool — dispatch to the typed tool clients.

In ``tool_mode="http"`` the tools call WS-4/WS-5; on ``mock`` (default) or any HTTP
error they return the deterministic mock string, so the graph runs offline in tests.
"""

from __future__ import annotations

from voice_agent.core.config import settings
from voice_agent.graph.agent_state import AgentState
from voice_agent.tools import (
    check_coverage,
    check_formulary,
    escalate,
    estimate_cost,
    find_provider,
)

_DISPATCH = {
    "check_coverage": check_coverage.run,
    "estimate_cost": estimate_cost.run,
    "find_provider": find_provider.run,
    "check_formulary": check_formulary.run,
    "escalate_to_human": escalate.run,
}


def _base_url(tool_name: str) -> str:
    if tool_name == "find_provider":
        return settings.providers_base_url
    return settings.eligibility_base_url


def call_tool(state: AgentState) -> AgentState:
    tool_name = state.get("tool_name", "escalate_to_human")
    question = state.get("question", "")

    # Use the real demo member for HTTP lookups until full member threading (M13).
    member_id = state.get("member_id") or ""
    if not member_id or member_id == "MOCK-MEMBER-001":
        member_id = "CVX-0042-MT"

    fn = _DISPATCH.get(tool_name, escalate.run)
    res = fn(question, member_id=member_id, mode=settings.tool_mode, base_url=_base_url(tool_name))

    return {
        **state,
        "tool_args": res.args,
        "tool_result": res.result,
        "tool_facts": res.facts,
    }
