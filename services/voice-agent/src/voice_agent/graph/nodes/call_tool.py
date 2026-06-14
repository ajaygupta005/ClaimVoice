"""Node: call_tool — dispatch to the mock tool implementations."""

from __future__ import annotations

import re
from typing import Any

from voice_agent.graph.agent_state import AgentState


# ── Mock tool implementations ─────────────────────────────────────────────────

def _check_coverage(question: str) -> tuple[str, dict[str, Any]]:
    match = re.search(
        r"\b(MRI|CT scan|colonoscopy|surgery|physical therapy|urgent care|ER|therapy|X.ray|ultrasound)\b",
        question, re.IGNORECASE,
    )
    service = match.group(0) if match else "the requested service"
    result = f"covered — {service} is a covered benefit under your plan"
    return result, {"service": service}


def _estimate_cost(question: str) -> tuple[str, dict[str, Any]]:
    if re.search(r"\b(copay|co-pay)\b", question, re.IGNORECASE):
        return "copay $30 in-network primary care / $75 urgent care / $50 specialist", {"query": question[:80]}
    if re.search(r"\bdeductible\b", question, re.IGNORECASE):
        return "deductible $1,500 / YTD spent $450 / remaining $1,050", {"query": question[:80]}
    if re.search(r"\b(oop|out.of.pocket)\b", question, re.IGNORECASE):
        return "OOP max $5,000 / YTD spent $1,200 / remaining $3,800", {"query": question[:80]}
    return "estimated cost $150–$250 negotiated rate", {"query": question[:80]}


def _find_provider(question: str) -> tuple[str, dict[str, Any]]:
    match = re.search(
        r"\b(cardiologist|dermatologist|orthopedist|psychiatrist|therapist|specialist|primary care|PCP)\b",
        question, re.IGNORECASE,
    )
    specialty = match.group(0) if match else "provider"
    return f"3 in-network {specialty}s found within 5 miles", {"specialty": specialty, "geo": "member location"}


def _check_formulary(question: str) -> tuple[str, dict[str, Any]]:
    match = re.search(
        r"\b(lisinopril|metformin|atorvastatin|humira|insulin|ozempic|adderall|[A-Z][a-z]+(?:mab|nib|stat|pril|olol))\b",
        question, re.IGNORECASE,
    )
    drug = match.group(0) if match else "the medication"
    if re.search(r"\b(humira|biologic)\b", question, re.IGNORECASE):
        return f"{drug} — specialty tier, requires prior authorization", {"drug": drug}
    return f"{drug} — Tier 1 generic, $10 copay / $25 mail-order 90-day", {"drug": drug}


def _escalate_to_human(_question: str) -> tuple[str, dict[str, Any]]:
    return "escalated — intent unclear or outside AI scope", {"reason": "intent unclear"}


_TOOL_DISPATCH = {
    "check_coverage": _check_coverage,
    "estimate_cost": _estimate_cost,
    "find_provider": _find_provider,
    "check_formulary": _check_formulary,
    "escalate_to_human": _escalate_to_human,
}


def call_tool(state: AgentState) -> AgentState:
    tool_name = state.get("tool_name", "escalate_to_human")
    question = state.get("question", "")
    fn = _TOOL_DISPATCH.get(tool_name, _escalate_to_human)
    result_str, args = fn(question)
    return {
        **state,
        "tool_args": args,
        "tool_result": result_str,
    }
