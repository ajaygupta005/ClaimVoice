"""
Grounded answer orchestrator (Component 26).

Takes a final transcript text, classifies intent via keyword routing, calls
the appropriate mock tool, and returns an AnswerFinalEvent ready for TTS.

Intent classes
--------------
  coverage   — questions about whether a service/procedure is covered
  cost       — questions about copay, coinsurance, deductible, OOP max
  provider   — questions about finding a doctor / specialist / facility
  formulary  — questions about drugs, prescriptions, formulary tiers
  escalate   — anything else, or low-confidence matches

Interface is intentionally synchronous and tool-agnostic so it can be
swapped for Claude / LangGraph without changing the WebSocket layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from voice_agent.schemas.answer import AnswerFinalEvent, ToolTrace
from voice_agent.schemas.transcript import FinalTranscriptEvent

# ── Intent classification ─────────────────────────────────────────────────────

_COVERAGE_PATTERNS = re.compile(
    r"\b(covered|coverage|cover|does my plan|is it covered|prior auth|authorization)\b",
    re.IGNORECASE,
)
_COST_PATTERNS = re.compile(
    r"\b(cost|copay|co-pay|coinsurance|deductible|out.of.pocket|oop|how much|pay|owe|price)\b",
    re.IGNORECASE,
)
_PROVIDER_PATTERNS = re.compile(
    r"\b(doctor|physician|specialist|provider|cardiologist|dermatologist|find|near|network|clinic|hospital|facility)\b",
    re.IGNORECASE,
)
_FORMULARY_PATTERNS = re.compile(
    r"\b(drug|medication|medicine|prescription|formulary|tier|rx|lisinopril|humira|metformin|insulin)\b",
    re.IGNORECASE,
)


def _classify_intent(text: str) -> str:
    scores: dict[str, int] = {
        "coverage": len(_COVERAGE_PATTERNS.findall(text)),
        "cost": len(_COST_PATTERNS.findall(text)),
        "provider": len(_PROVIDER_PATTERNS.findall(text)),
        "formulary": len(_FORMULARY_PATTERNS.findall(text)),
    }
    best_intent, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best_intent if best_score > 0 else "escalate"


# ── Mock tool implementations ─────────────────────────────────────────────────

def _mock_check_coverage(text: str) -> tuple[str, ToolTrace]:
    # Extract a rough service name from the question
    match = re.search(
        r"\b(MRI|CT scan|colonoscopy|surgery|physical therapy|urgent care|ER|therapy|X.ray|ultrasound)\b",
        text, re.IGNORECASE,
    )
    service = match.group(0) if match else "the requested service"
    result = f"covered — {service} is a covered benefit under your plan"
    answer = (
        f"Yes, {service} is covered under your plan. "
        "Since you have not yet met your deductible, you will pay the negotiated rate "
        "up to your remaining deductible, then your plan covers the rest."
    )
    trace = ToolTrace(tool="check_coverage", args={"service": service}, result=result, ok=True)
    return answer, trace


def _mock_estimate_cost(text: str) -> tuple[str, ToolTrace]:
    if re.search(r"\b(copay|co-pay)\b", text, re.IGNORECASE):
        result = "copay $30 in-network primary care / $75 urgent care"
        answer = (
            "Your in-network copay is $30 for a primary care visit and $75 for urgent care. "
            "Specialist visits are $50 copay."
        )
    elif re.search(r"\bdeductible\b", text, re.IGNORECASE):
        result = "deductible $1,500 / YTD spent $450 / remaining $1,050"
        answer = (
            "Your annual deductible is $1,500. You have spent $450 so far this year, "
            "so you have $1,050 remaining before your plan pays 100%."
        )
    elif re.search(r"\b(oop|out.of.pocket)\b", text, re.IGNORECASE):
        result = "OOP max $5,000 / YTD spent $1,200 / remaining $3,800"
        answer = (
            "Your out-of-pocket maximum is $5,000. You have spent $1,200 this year, "
            "so you have $3,800 remaining."
        )
    else:
        result = "estimated cost $150–$250 negotiated rate"
        answer = (
            "Based on your plan, the estimated cost for this service is $150 to $250 "
            "at the negotiated in-network rate, applied toward your deductible."
        )
    trace = ToolTrace(tool="estimate_cost", args={"query": text[:80]}, result=result, ok=True)
    return answer, trace


def _mock_find_provider(text: str) -> tuple[str, ToolTrace]:
    match = re.search(
        r"\b(cardiologist|dermatologist|orthopedist|psychiatrist|therapist|specialist|primary care|PCP)\b",
        text, re.IGNORECASE,
    )
    specialty = match.group(0) if match else "provider"
    result = f"3 in-network {specialty}s found within 5 miles"
    answer = (
        f"I found three in-network {specialty}s near you. "
        "The closest is Dr. Sarah Chen at 425 Madison Ave, accepting new patients. "
        "Would you like me to provide more details or help schedule an appointment?"
    )
    trace = ToolTrace(tool="find_provider", args={"specialty": specialty, "geo": "member location"}, result=result, ok=True)
    return answer, trace


def _mock_check_formulary(text: str) -> tuple[str, ToolTrace]:
    match = re.search(
        r"\b(lisinopril|metformin|atorvastatin|humira|insulin|ozempic|adderall|[A-Z][a-z]+(?:mab|nib|stat|pril|olol))\b",
        text, re.IGNORECASE,
    )
    drug = match.group(0) if match else "the medication"
    # Humira / biologics get a different response
    if re.search(r"\b(humira|biologic)\b", text, re.IGNORECASE):
        result = f"{drug} — specialty tier, requires prior authorization"
        answer = (
            f"{drug} is covered as a specialty-tier medication and requires prior authorization. "
            "Please have your prescriber submit a prior auth request. Allow 3–5 business days."
        )
    else:
        result = f"{drug} — Tier 1 generic, $10 copay"
        answer = (
            f"Yes, {drug} is on your formulary as a Tier 1 generic. "
            "Your copay is $10 for a 30-day supply or $25 for a 90-day mail-order supply."
        )
    trace = ToolTrace(tool="check_formulary", args={"drug": drug}, result=result, ok=True)
    return answer, trace


def _escalate(text: str) -> tuple[str, ToolTrace]:
    result = "escalated — intent unclear or outside AI scope"
    answer = (
        "I want to make sure you get the most accurate information. "
        "Let me connect you with a benefits specialist who can answer your question directly."
    )
    trace = ToolTrace(tool="escalate_to_human", args={"reason": "intent unclear"}, result=result, ok=False)
    return answer, trace


# ── Orchestrator ──────────────────────────────────────────────────────────────

_INTENT_HANDLERS = {
    "coverage": _mock_check_coverage,
    "cost": _mock_estimate_cost,
    "provider": _mock_find_provider,
    "formulary": _mock_check_formulary,
    "escalate": _escalate,
}


def orchestrate(transcript: FinalTranscriptEvent) -> AnswerFinalEvent:
    """
    Classify the transcript intent, call the mock tool, return AnswerFinalEvent.
    Empty or very short transcripts are always escalated.
    """
    text = transcript.text.strip()
    if len(text) < 3:
        intent = "escalate"
    else:
        intent = _classify_intent(text)

    handler = _INTENT_HANDLERS[intent]
    answer_text, trace = handler(text)
    grounded = trace.ok

    return AnswerFinalEvent(
        callSid=transcript.callSid,
        streamSid=transcript.streamSid,
        intent=intent,
        text=answer_text,
        grounded=grounded,
        tool_trace=[trace],
    )
