"""Node: prepare_response — finalise the answer, tool trace, and escalation flag.

Enforces the project's hallucination-guard contract ("Claude narrates only if
grounded"): if the composer produced a factual answer that the guard flagged as
ungrounded, the unverified answer is replaced with a safe escalation message so
the unsupported claim is never spoken. Also reflects the guard result onto the
``ok`` field of real-tool trace entries (escalate_to_human stays ok=False).
"""

from __future__ import annotations

from voice_agent.graph.agent_state import AgentState

# Spoken when a factual answer fails the hallucination guard — we decline to
# surface the unverified claim and hand off to a human instead.
_UNVERIFIED_FALLBACK = (
    "I want to make sure I only give you accurate information, and I couldn't fully "
    "verify that against your plan details. Let me connect you with a benefits "
    "specialist who can confirm the specifics for you."
)


def prepare_response(state: AgentState) -> AgentState:
    existing_trace: list = list(state.get("tool_trace") or [])
    grounded = bool(state.get("grounded", False))
    intent = state.get("intent", "escalate")
    answer_text = state.get("answer_text", "")
    escalate = intent == "escalate"

    # "Narrate only if grounded": a factual intent whose answer failed the guard
    # must not surface the unverified claim — replace it with a safe handoff.
    if not grounded and not escalate:
        answer_text = _UNVERIFIED_FALLBACK
        escalate = True

    # Reflect guard result on the ok flag of real tool entries.
    # escalate_to_human entries are always ok=False (no factual claim).
    for entry in existing_trace:
        if entry.get("tool") != "escalate_to_human":
            entry["ok"] = grounded

    return {
        **state,
        "answer_text": answer_text,
        "tool_trace": existing_trace,
        "escalate": escalate,
    }
