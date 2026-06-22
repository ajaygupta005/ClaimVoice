"""Node: call_tool — dispatch to the typed tool clients.

In ``tool_mode="http"`` the tools call WS-4/WS-5 directly and return typed errors on
failure instead of silently falling back to demo data.

Member context rules:
  - Real mode (tool_mode="http", demo_mode=False): a missing or placeholder member_id
    returns a safe "needs clarification" result without calling the backend.
  - Demo mode (demo_mode=True, the default): missing member falls back to the seeded
    demo member CVX-0042-MT so that local dev and UI demos work offline.
  - Mock mode (tool_mode="mock"): always runs deterministic inline logic; member_id
    is irrelevant.

Tool trace items include ``data_source`` ("real" | "demo" | "error") and ``error_code``
so callers can distinguish live results from demo data without inspecting the result text.
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
from voice_agent.tools.schemas import ToolResult

_DISPATCH = {
    "check_coverage": check_coverage.run,
    "estimate_cost": estimate_cost.run,
    "find_provider": find_provider.run,
    "check_formulary": check_formulary.run,
    "escalate_to_human": escalate.run,
}

# Member IDs treated as "no real member" — only used in mock/demo mode.
_PLACEHOLDER_IDS = {"", "MOCK-MEMBER-001"}

_SAFE_NO_MEMBER = ToolResult(
    result=(
        "I need to verify your identity before I can access your plan details. "
        "Could you please provide your member ID or date of birth?"
    ),
    args={"member_id": ""},
    ok=False,
    facts=[],
    data_source="error",
    error_code="missing_member",
)


def _base_url(tool_name: str) -> str:
    if tool_name == "find_provider":
        return settings.providers_base_url
    return settings.eligibility_base_url


def _resolve_member(raw_member_id: str) -> tuple[str, str]:
    """Return (resolved_id, member_source).

    member_source is "provided" when the caller supplied a real ID, "demo" when
    we fell back to the seeded demo member, or "missing" when neither is available.
    """
    if raw_member_id and raw_member_id not in _PLACEHOLDER_IDS:
        return raw_member_id, "provided"
    if settings.demo_mode:
        return "CVX-0042-MT", "demo"
    return "", "missing"


def call_tool(state: AgentState) -> AgentState:
    tool_name = state.get("tool_name", "escalate_to_human")
    question = state.get("question", "")
    raw_member_id = state.get("member_id") or ""

    member_id, member_source = _resolve_member(raw_member_id)

    # In real (non-demo) HTTP mode, refuse to call tools without a member ID.
    if settings.tool_mode == "http" and not settings.demo_mode and member_source == "missing":
        res: ToolResult = _SAFE_NO_MEMBER
    else:
        fn = _DISPATCH.get(tool_name, escalate.run)
        res = fn(question, member_id=member_id, mode=settings.tool_mode, base_url=_base_url(tool_name))

    # Build the trace entry with source metadata.
    existing_trace: list = list(state.get("tool_trace") or [])
    trace_entry = {
        "tool": tool_name,
        "args": res.args,
        "result": res.result,
        "ok": res.ok,
        "data_source": res.data_source,
        "error_code": res.error_code,
        "member_source": member_source,
    }

    return {
        **state,
        "tool_args": res.args,
        "tool_result": res.result,
        "tool_facts": res.facts,
        "tool_trace": existing_trace + [trace_entry],
        "member_id": member_id,
        "plan_id": res.args.get("planId") or state.get("plan_id", ""),
    }
