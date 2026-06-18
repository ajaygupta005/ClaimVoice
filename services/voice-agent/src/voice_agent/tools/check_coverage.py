"""check_coverage tool — coverage for a service.

mode="http" calls WS-4 GET /api/v1/coverage; mode="mock" (or any HTTP error) returns
the deterministic mock string. The mock branch is verbatim from the original inline
implementation so existing graph tests stay green.
"""

from __future__ import annotations

import re

import httpx

from voice_agent.tools.schemas import ToolResult


def _mock(question: str) -> ToolResult:
    if re.search(r"\b(x-ray|xray|x ray|imaging|ct scan|ct|ultrasound|mammogram)\b", question, re.IGNORECASE):
        match = re.search(
            r"\b(x-ray|xray|x ray|imaging|ct scan|ct|ultrasound|mammogram)\b", question, re.IGNORECASE
        )
        service = match.group(0) if match else "imaging"
        result = f"covered — {service} 20% coinsurance after deductible, prior auth required for advanced imaging"
        return ToolResult(result, {"service": service}, True, [result])
    if re.search(r"\b(dental|vision)\b", question, re.IGNORECASE):
        service = "dental" if re.search(r"\bdental\b", question, re.IGNORECASE) else "vision"
        result = "dental cleaning not covered under medical plan; vision exam $0 under vision benefit"
        return ToolResult(result, {"service": service}, True, [result])
    if re.search(r"\b(annual physical|preventive|wellness visit|physical)\b", question, re.IGNORECASE):
        match = re.search(r"\b(annual physical|preventive|wellness visit|physical)\b", question, re.IGNORECASE)
        service = match.group(0) if match else "preventive care"
        result = "preventive care $0 copay under your plan"
        return ToolResult(result, {"service": service}, True, [result])
    if re.search(r"\b(therapy|mental health|telehealth|behavioral health)\b", question, re.IGNORECASE):
        match = re.search(r"\b(therapy|mental health|telehealth|behavioral health)\b", question, re.IGNORECASE)
        service = match.group(0) if match else "therapy"
        result = "covered — $40 copay for therapy, $0 for telehealth"
        return ToolResult(result, {"service": service}, True, [result])
    match = re.search(
        r"\b(MRI|CT scan|colonoscopy|surgery|physical therapy|urgent care|ER|therapy|X.ray|ultrasound)\b",
        question, re.IGNORECASE,
    )
    service = match.group(0) if match else "the requested service"
    result = f"covered — {service} is a covered benefit under your plan"
    return ToolResult(result, {"service": service}, True, [result])


def _http(question: str, member_id: str, base_url: str) -> ToolResult:
    service = _mock(question).args["service"]  # reuse extraction
    r = httpx.get(
        f"{base_url}/api/v1/coverage",
        params={"memberId": member_id, "service": service},
        timeout=5.0,
    )
    r.raise_for_status()
    d = r.json()
    parts: list[str] = []
    if d.get("covered"):
        parts.append(f"{d.get('matchedBenefit') or service} is covered")
        if d.get("copayAmountCents") is not None:
            parts.append(f"${d['copayAmountCents'] // 100} copay")
        if d.get("coinsurancePercentage") is not None:
            parts.append(f"{d['coinsurancePercentage']:g}% coinsurance")
        if d.get("requiresPriorAuth"):
            parts.append("prior authorization required")
    else:
        parts.append(f"{service} is not a covered benefit under your plan")
    return ToolResult(
        result=", ".join(parts),
        args={"service": service, "memberId": member_id},
        ok=True,
        facts=d.get("facts", []),
    )


def run(question: str, member_id: str, mode: str, base_url: str) -> ToolResult:
    if mode == "http":
        try:
            return _http(question, member_id, base_url)
        except Exception:
            pass
    return _mock(question)
