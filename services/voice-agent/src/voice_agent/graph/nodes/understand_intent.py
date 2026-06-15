"""Node: understand_intent — deterministic keyword routing."""

from __future__ import annotations

import re

from voice_agent.graph.agent_state import AgentState

_COVERAGE = re.compile(
    r"\b(covered|coverage|cover|does my plan|prior auth|authorization|"
    r"x-ray|x ray|xray|imaging|dental|vision|scan|ct scan|mammogram|ultrasound|"
    r"annual physical|preventive|wellness visit|therapy|mental health|telehealth|colonoscopy)\b",
    re.IGNORECASE,
)
_COST = re.compile(
    r"\b(cost|copay|co-pay|coinsurance|deductible|out.of.pocket|oop|how much|pay|owe|price)\b",
    re.IGNORECASE,
)
_PROVIDER = re.compile(
    r"\b(doctor|physician|specialist|provider|cardiologist|dermatologist|find|near|network|clinic|hospital|facility|"
    r"primary care|PCP|imaging center|radiology|nearest|where can i get|where can i find)\b",
    re.IGNORECASE,
)
_FORMULARY = re.compile(
    r"\b(drug|medication|medicine|prescription|formulary|tier|rx|lisinopril|humira|metformin|insulin)\b",
    re.IGNORECASE,
)
# Capability / help questions — matched before keyword scoring to avoid escalation
_HELP = re.compile(
    r"\b(what can you do|help me|how do you work|what do you know|tell me about yourself|"
    r"what are you|who are you|what can i ask|what questions|can you help|"
    r"what services|capabilities|what do you help with|what topics|guide me|introduction)\b",
    re.IGNORECASE,
)

# Dual-signal patterns for tie-breaking
_COVERAGE_SIGNAL = re.compile(r"\b(covered|coverage)\b", re.IGNORECASE)
_PROVIDER_SIGNAL = re.compile(
    r"\b(doctor|physician|specialist|provider|cardiologist|dermatologist|find|near|network|clinic|hospital|facility|"
    r"primary care|PCP|imaging center|radiology|nearest|where can i get|where can i find)\b",
    re.IGNORECASE,
)

_INTENT_TO_TOOL: dict[str, str] = {
    "coverage": "check_coverage",
    "cost": "estimate_cost",
    "provider": "find_provider",
    "formulary": "check_formulary",
    "help": "escalate_to_human",   # reuses escalation tool but compose_answer intercepts
    "escalate": "escalate_to_human",
}


def understand_intent(state: AgentState) -> AgentState:
    text = state.get("question", "")
    if len(text.strip()) < 3:
        intent = "escalate"
    elif _HELP.search(text):
        intent = "help"
    else:
        scores = {
            "coverage": len(_COVERAGE.findall(text)),
            "cost": len(_COST.findall(text)),
            "provider": len(_PROVIDER.findall(text)),
            "formulary": len(_FORMULARY.findall(text)),
        }
        best, best_score = max(scores.items(), key=lambda kv: kv[1])

        if best_score == 0:
            intent = "escalate"
        elif scores["coverage"] > 0 and scores["provider"] > 0 and scores["coverage"] == scores["provider"]:
            # Tie-breaking: prefer coverage if "covered" or "coverage" appears, else provider
            if _COVERAGE_SIGNAL.search(text):
                intent = "coverage"
            else:
                # Dual-signal short-circuit: queries containing imaging/scan terms with "where can i get"
                # or similar provider-locator phrases route to coverage when they carry imaging keywords
                intent = "coverage" if re.search(
                    r"\b(x-ray|x ray|xray|imaging|scan|ct scan|mammogram|ultrasound)\b",
                    text, re.IGNORECASE,
                ) else "provider"
        else:
            intent = best

    return {
        **state,
        "intent": intent,
        "tool_name": _INTENT_TO_TOOL[intent],
        "tool_args": {"question": text},
    }
