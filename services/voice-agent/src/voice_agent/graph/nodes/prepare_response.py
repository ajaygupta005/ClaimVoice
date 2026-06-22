"""Node: prepare_response — finalise tool trace and mark escalation flag.

Preserves the trace built by call_tool (with data_source / error_code /
member_source from C62) and updates the ``ok`` field on real-tool entries
to reflect whether the hallucination guard passed.
"""

from __future__ import annotations

from voice_agent.graph.agent_state import AgentState


def prepare_response(state: AgentState) -> AgentState:
    existing_trace: list = list(state.get("tool_trace") or [])
    grounded = bool(state.get("grounded", False))
    intent = state.get("intent", "escalate")

    # Reflect guard result on the ok flag of real tool entries.
    # escalate_to_human entries are always ok=False (no factual claim).
    for entry in existing_trace:
        if entry.get("tool") != "escalate_to_human":
            entry["ok"] = grounded

    return {
        **state,
        "tool_trace": existing_trace,
        "escalate": intent == "escalate",
    }
