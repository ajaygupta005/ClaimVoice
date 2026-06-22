"""check_formulary tool — drug coverage/tier.

mode="http" calls WS-4 GET /api/v1/formulary/lookup; mode="mock" returns deterministic
demo data. HTTP errors produce a safe clarification result.
"""

from __future__ import annotations

import re

import httpx

from voice_agent.tools.schemas import ToolResult

_DRUG = re.compile(
    r"\b(lisinopril|metformin|atorvastatin|humira|insulin|ozempic|adderall|"
    r"[A-Z][a-z]+(?:mab|nib|stat|pril|olol))\b",
    re.IGNORECASE,
)


def _extract_drug(question: str) -> str:
    m = _DRUG.search(question)
    return m.group(0) if m else "the medication"


def _mock(question: str) -> ToolResult:
    drug = _extract_drug(question)
    if re.search(r"\b(humira|biologic)\b", question, re.IGNORECASE):
        result = f"{drug} — specialty tier, requires prior authorization"
    else:
        result = f"{drug} — Tier 1 generic, $10 copay / $25 mail-order 90-day"
    return ToolResult(result, {"drug": drug}, True, [result], data_source="demo")


def _http(question: str, member_id: str, base_url: str) -> ToolResult:
    drug = _extract_drug(question)
    try:
        r = httpx.get(
            f"{base_url}/api/v1/formulary/lookup",
            params={"memberId": member_id, "drug": drug},
            timeout=5.0,
        )
    except httpx.TimeoutException:
        return ToolResult(
            result="I'm unable to check the formulary right now — the service timed out.",
            args={"drug": drug, "memberId": member_id},
            ok=False,
            facts=[],
            data_source="error",
            error_code="service_unavailable",
        )
    except httpx.RequestError:
        return ToolResult(
            result="I'm unable to reach the formulary service right now.",
            args={"drug": drug, "memberId": member_id},
            ok=False,
            facts=[],
            data_source="error",
            error_code="service_unavailable",
        )
    if r.status_code == 404:
        return ToolResult(
            result="I couldn't find your formulary information. Please verify your member ID.",
            args={"drug": drug, "memberId": member_id},
            ok=False,
            facts=[],
            data_source="error",
            error_code="member_not_found",
        )
    if not r.is_success:
        return ToolResult(
            result="I'm unable to check the formulary right now.",
            args={"drug": drug, "memberId": member_id},
            ok=False,
            facts=[],
            data_source="error",
            error_code="service_unavailable",
        )
    d = r.json()
    facts = d.get("facts", [])
    match = d.get("match")
    if match:
        tier = match.get("formularyTier")
        pa = " requires prior authorization" if match.get("priorAuthRequired") else ""
        result = f"{match.get('drugName', drug)} — Tier {tier}{pa}"
    else:
        result = f"{drug} is not on your plan formulary"
    return ToolResult(
        result=result,
        args={"drug": drug, "memberId": member_id, "planId": str(d.get("planId") or "")},
        ok=True,
        facts=facts,
        data_source="real",
    )


def run(question: str, member_id: str, mode: str, base_url: str) -> ToolResult:
    if mode == "http":
        return _http(question, member_id, base_url)
    return _mock(question)
