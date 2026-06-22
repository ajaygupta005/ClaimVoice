"""Node: prepare_response — finalise the answer, tool trace, and escalation flag.

Enforces the hallucination-guard contract for benefit-figure answers ("Claude
narrates only if grounded"): if a cost / coverage / formulary answer fails the
guard, the unverified claim (a copay, deductible, tier, or coverage decision) is
replaced with a safe escalation instead of being spoken.

Provider listings are intentionally NOT gated here. The guard can't reliably
verify a directory result (names/distances vary in phrasing), so a flaky flag
must not drop the member into an escalation — the provider list is still shown.

Also reflects the guard result onto the ``ok`` field of real-tool trace entries
(escalate_to_human stays ok=False).
"""

from __future__ import annotations

from voice_agent.graph.agent_state import AgentState

# Spoken when a benefit-figure answer fails the hallucination guard — we decline
# to surface the unverified claim and hand off to a human instead.
_UNVERIFIED_FALLBACK = (
    "I want to make sure I only give you accurate information, and I couldn't fully "
    "verify that against your plan details. Let me connect you with a benefits "
    "specialist who can confirm the specifics for you."
)

# Intents whose answers assert specific benefit figures (copays, deductibles,
# tiers, coverage yes/no) where surfacing an unverified claim is dangerous.
_GUARDED_INTENTS = {"cost", "coverage", "formulary"}


def prepare_response(state: AgentState) -> AgentState:
    existing_trace: list = list(state.get("tool_trace") or [])
    grounded = bool(state.get("grounded", False))
    intent = state.get("intent", "escalate")
    answer_text = state.get("answer_text", "")
    escalate = intent == "escalate"

    # "Narrate only if grounded" for benefit-figure answers: replace an
    # unverified cost/coverage/formulary answer with a safe handoff.
    if not grounded and intent in _GUARDED_INTENTS:
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
