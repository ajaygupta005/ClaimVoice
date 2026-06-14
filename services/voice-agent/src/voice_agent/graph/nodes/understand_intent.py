"""Node: understand_intent — deterministic keyword routing."""

from __future__ import annotations

import re

from voice_agent.graph.agent_state import AgentState

_COVERAGE = re.compile(
    r"\b(covered|coverage|cover|does my plan|prior auth|authorization)\b",
    re.IGNORECASE,
)
_COST = re.compile(
    r"\b(cost|copay|co-pay|coinsurance|deductible|out.of.pocket|oop|how much|pay|owe|price)\b",
    re.IGNORECASE,
)
_PROVIDER = re.compile(
    r"\b(doctor|physician|specialist|provider|cardiologist|dermatologist|find|near|network|clinic|hospital|facility)\b",
    re.IGNORECASE,
)
_FORMULARY = re.compile(
    r"\b(drug|medication|medicine|prescription|formulary|tier|rx|lisinopril|humira|metformin|insulin)\b",
    re.IGNORECASE,
)

_INTENT_TO_TOOL: dict[str, str] = {
    "coverage": "check_coverage",
    "cost": "estimate_cost",
    "provider": "find_provider",
    "formulary": "check_formulary",
    "escalate": "escalate_to_human",
}


def understand_intent(state: AgentState) -> AgentState:
    text = state.get("question", "")
    if len(text.strip()) < 3:
        intent = "escalate"
    else:
        scores = {
            "coverage": len(_COVERAGE.findall(text)),
            "cost": len(_COST.findall(text)),
            "provider": len(_PROVIDER.findall(text)),
            "formulary": len(_FORMULARY.findall(text)),
        }
        best, best_score = max(scores.items(), key=lambda kv: kv[1])
        intent = best if best_score > 0 else "escalate"

    return {
        **state,
        "intent": intent,
        "tool_name": _INTENT_TO_TOOL[intent],
        "tool_args": {"question": text},
    }
