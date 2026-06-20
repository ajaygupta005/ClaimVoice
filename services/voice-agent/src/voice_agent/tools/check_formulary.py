"""check_formulary tool — drug coverage/tier. http -> WS-4 GET /formulary/lookup."""

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
    return ToolResult(result, {"drug": drug}, True, [result])


def _http(question: str, member_id: str, base_url: str) -> ToolResult:
    drug = _extract_drug(question)
    r = httpx.get(
        f"{base_url}/api/v1/formulary/lookup",
        params={"memberId": member_id, "drug": drug},
        timeout=5.0,
    )
    r.raise_for_status()
    d = r.json()
    facts = d.get("facts", [])
    match = d.get("match")
    if match:
        tier = match.get("formularyTier")
        pa = " requires prior authorization" if match.get("priorAuthRequired") else ""
        result = f"{match.get('drugName', drug)} — Tier {tier}{pa}"
    else:
        result = f"{drug} is not on your plan formulary"
    return ToolResult(result=result, args={"drug": drug, "memberId": member_id}, ok=True, facts=facts)


def run(question: str, member_id: str, mode: str, base_url: str) -> ToolResult:
    if mode == "http":
        try:
            return _http(question, member_id, base_url)
        except Exception:
            pass
    return _mock(question)
