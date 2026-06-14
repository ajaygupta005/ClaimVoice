"""Node: prepare_response — build ToolTrace entry and mark TTS ready."""

from __future__ import annotations

from voice_agent.graph.agent_state import AgentState


def prepare_response(state: AgentState) -> AgentState:
    trace_entry = {
        "tool": state.get("tool_name", "escalate_to_human"),
        "args": state.get("tool_args", {}),
        "result": state.get("tool_result", ""),
        "ok": state.get("grounded", False),
    }
    return {
        **state,
        "tool_trace": [trace_entry],
        "escalate": state.get("intent") == "escalate",
    }
