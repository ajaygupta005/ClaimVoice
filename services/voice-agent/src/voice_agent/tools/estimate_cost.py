"""estimate_cost tool — copay/deductible/OOP.

mode="http" calls WS-4 POST /api/v1/cost/estimate; mode="mock" returns deterministic
demo data. HTTP errors produce a safe clarification result.
"""

from __future__ import annotations

import re

import httpx

from voice_agent.tools.schemas import ToolResult


def _cost_type(question: str) -> str:
    if re.search(r"\b(copay|co-pay)\b", question, re.IGNORECASE):
        return "copay"
    if re.search(r"\bdeduc", question, re.IGNORECASE):  # deductible / deduction (STT variants)
        return "deductible"
    if re.search(r"\b(oop|out.of.pocket)\b", question, re.IGNORECASE):
        return "oop"
    return "service"


def _service_term(question: str) -> str | None:
    if re.search(r"\b(pcp|primary care)\b", question, re.IGNORECASE):
        return "primary care"
    m = re.search(
        r"\b(urgent care|specialist|emergency|ER|MRI|imaging|telehealth)\b", question, re.IGNORECASE
    )
    return m.group(0) if m else None


def _mock(question: str) -> ToolResult:
    if re.search(r"\b(copay|co-pay)\b", question, re.IGNORECASE):
        result = "copay $30 in-network primary care / $75 urgent care / $50 specialist"
    elif re.search(r"\bdeduc", question, re.IGNORECASE):  # deductible / deduction (STT variants)
        result = "deductible $1,500 / YTD spent $450 / remaining $1,050"
    elif re.search(r"\b(oop|out.of.pocket)\b", question, re.IGNORECASE):
        result = "OOP max $5,000 / YTD spent $1,200 / remaining $3,800"
    else:
        result = "estimated cost $150–$250 negotiated rate"
    return ToolResult(result, {"query": question[:80]}, True, [result], data_source="demo")


def _http(question: str, member_id: str, base_url: str) -> ToolResult:
    cost_type = _cost_type(question)
    service = _service_term(question)
    try:
        r = httpx.post(
            f"{base_url}/api/v1/cost/estimate",
            json={"memberId": member_id, "costType": cost_type, "service": service},
            timeout=5.0,
        )
    except httpx.TimeoutException:
        return ToolResult(
            result="I'm unable to retrieve cost information right now — the service timed out. Please try again.",
            args={"costType": cost_type, "service": service, "memberId": member_id},
            ok=False,
            facts=[],
            data_source="error",
            error_code="service_unavailable",
        )
    except httpx.RequestError:
        return ToolResult(
            result="I'm unable to reach the cost estimation service right now.",
            args={"costType": cost_type, "service": service, "memberId": member_id},
            ok=False,
            facts=[],
            data_source="error",
            error_code="service_unavailable",
        )
    if r.status_code == 404:
        return ToolResult(
            result="I couldn't find cost information for your plan. Please verify your member ID.",
            args={"costType": cost_type, "service": service, "memberId": member_id},
            ok=False,
            facts=[],
            data_source="error",
            error_code="member_not_found",
        )
    if not r.is_success:
        return ToolResult(
            result="I'm unable to retrieve cost information right now.",
            args={"costType": cost_type, "service": service, "memberId": member_id},
            ok=False,
            facts=[],
            data_source="error",
            error_code="service_unavailable",
        )
    d = r.json()
    facts = d.get("facts", [])
    result = "; ".join(facts) if facts else "no cost information found"
    return ToolResult(
        result=result,
        args={"costType": cost_type, "service": service, "memberId": member_id},
        ok=True,
        facts=facts,
        data_source="real",
    )


def run(question: str, member_id: str, mode: str, base_url: str) -> ToolResult:
    if mode == "http":
        return _http(question, member_id, base_url)
    return _mock(question)
