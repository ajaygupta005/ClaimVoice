"""Node: call_tool — dispatch to the mock tool implementations."""

from __future__ import annotations

import re
from typing import Any

from voice_agent.graph.agent_state import AgentState


# ── Mock tool implementations ─────────────────────────────────────────────────

def _check_coverage(question: str) -> tuple[str, dict[str, Any]]:
    # Imaging / radiology bucket
    if re.search(r"\b(x-ray|xray|x ray|imaging|ct scan|ct|ultrasound|mammogram)\b", question, re.IGNORECASE):
        match = re.search(
            r"\b(x-ray|xray|x ray|imaging|ct scan|ct|ultrasound|mammogram)\b",
            question, re.IGNORECASE,
        )
        service = match.group(0) if match else "imaging"
        return (
            f"covered — {service} 20% coinsurance after deductible, prior auth required for advanced imaging",
            {"service": service},
        )
    # Dental / vision bucket
    if re.search(r"\b(dental|vision)\b", question, re.IGNORECASE):
        service = "dental" if re.search(r"\bdental\b", question, re.IGNORECASE) else "vision"
        return (
            "dental cleaning not covered under medical plan; vision exam $0 under vision benefit",
            {"service": service},
        )
    # Preventive / annual physical bucket
    if re.search(r"\b(annual physical|preventive|wellness visit|physical)\b", question, re.IGNORECASE):
        match = re.search(
            r"\b(annual physical|preventive|wellness visit|physical)\b",
            question, re.IGNORECASE,
        )
        service = match.group(0) if match else "preventive care"
        return "preventive care $0 copay under your plan", {"service": service}
    # Mental health / therapy / telehealth bucket
    if re.search(r"\b(therapy|mental health|telehealth|behavioral health)\b", question, re.IGNORECASE):
        match = re.search(
            r"\b(therapy|mental health|telehealth|behavioral health)\b",
            question, re.IGNORECASE,
        )
        service = match.group(0) if match else "therapy"
        return "covered — $40 copay for therapy, $0 for telehealth", {"service": service}
    # Generic fallback — also handles original keywords
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
    # Imaging / radiology bucket
    if re.search(r"\b(x-ray|xray|x ray|imaging|radiolog|radiology|imaging center)\b", question, re.IGNORECASE):
        specialty = "imaging"
        return (
            "2 in-network imaging centers within 3 miles — RadNet at 400 Madison Ave (in-network), "
            "City Imaging at 55 W 45th St (in-network)",
            {"specialty": specialty, "geo": "member location"},
        )
    # Primary care / PCP bucket
    if re.search(r"\b(primary care|PCP)\b", question, re.IGNORECASE):
        specialty = "primary care"
        return (
            "3 in-network primary care providers found — Dr. Rachel Kim 0.4 mi (accepting patients), "
            "Dr. Elena Varga 0.8 mi, Dr. James Park 1.2 mi",
            {"specialty": specialty, "geo": "member location"},
        )
    match = re.search(
        r"\b(cardiologist|dermatologist|orthopedist|psychiatrist|therapist|specialist|primary care|PCP|"
        r"radiologist|imaging center|urgent care|gynecologist|OB-GYN|ophthalmologist|optometrist)\b",
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
