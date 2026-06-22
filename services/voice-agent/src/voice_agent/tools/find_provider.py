"""find_provider tool — nearby in-network providers.

mode="http" calls WS-5 GET /api/v1/providers/near; mode="mock" returns deterministic
demo data. HTTP errors produce a safe clarification result.
"""

from __future__ import annotations

import re

import httpx

from voice_agent.tools.schemas import ToolResult

# Default member geo (Midtown Manhattan) until real member context is threaded.
_DEFAULT_GEO = (40.7580, -73.9855)


def _extract_specialty(question: str) -> str:
    match = re.search(
        r"\b(internal medicine|family medicine|family practice|pediatric(?:ian)?s?|"
        r"psychiatr(?:ist|y)|emergency(?: medicine)?|cardiolog(?:ist|y)|dermatolog(?:ist|y)|"
        r"orthoped(?:ist|ics|ic surgery)|therapist|specialist|primary care|PCP|"
        r"radiologist|imaging center|urgent care|gynecologist|obstetrics|OB-GYN|"
        r"ophthalmologist|optometrist|x-ray|xray|x ray|imaging|radiolog|radiology)\b",
        question, re.IGNORECASE,
    )
    return match.group(0) if match else "provider"


def _mock(question: str) -> ToolResult:
    if re.search(r"\b(x-ray|xray|x ray|imaging|radiolog|radiology|imaging center)\b", question, re.IGNORECASE):
        result = (
            "2 in-network imaging centers within 3 miles — RadNet at 400 Madison Ave (in-network), "
            "City Imaging at 55 W 45th St (in-network)"
        )
        return ToolResult(result, {"specialty": "imaging", "geo": "member location"}, True, [result], data_source="demo")
    if re.search(r"\b(primary care|PCP)\b", question, re.IGNORECASE):
        result = (
            "3 in-network primary care providers found — Dr. Rachel Kim 0.4 mi (accepting patients), "
            "Dr. Elena Varga 0.8 mi, Dr. James Park 1.2 mi"
        )
        return ToolResult(result, {"specialty": "primary care", "geo": "member location"}, True, [result], data_source="demo")
    specialty = _extract_specialty(question)
    result = f"3 in-network {specialty}s found within 5 miles"
    return ToolResult(result, {"specialty": specialty, "geo": "member location"}, True, [result], data_source="demo")


def _provider_name(p: dict) -> str:
    return (
        p.get("organizationName")
        or " ".join(filter(None, [p.get("firstName"), p.get("lastName")]))
        or p.get("npi", "provider")
    )


def _http(question: str, member_id: str, base_url: str) -> ToolResult:
    specialty = _extract_specialty(question)
    lat, lng = _DEFAULT_GEO
    try:
        r = httpx.get(
            f"{base_url}/api/v1/providers/near",
            params={"specialty": specialty, "lat": lat, "lng": lng, "radiusKm": 25, "limit": 3},
            timeout=5.0,
        )
    except httpx.TimeoutException:
        return ToolResult(
            result="I'm unable to search for providers right now — the service timed out.",
            args={"specialty": specialty},
            ok=False,
            facts=[],
            data_source="error",
            error_code="service_unavailable",
        )
    except httpx.RequestError:
        return ToolResult(
            result="I'm unable to reach the provider directory right now.",
            args={"specialty": specialty},
            ok=False,
            facts=[],
            data_source="error",
            error_code="service_unavailable",
        )
    if not r.is_success:
        return ToolResult(
            result="I'm unable to search the provider directory right now.",
            args={"specialty": specialty},
            ok=False,
            facts=[],
            data_source="error",
            error_code="service_unavailable",
        )
    provs = r.json().get("providers", [])
    if not provs:
        result = f"No {specialty} providers were found near you in our directory."
        return ToolResult(
            result=result,
            args={"specialty": specialty},
            ok=True,
            facts=[result],
            data_source="real",
            error_code="no_results",
        )
    facts = [
        f"{_provider_name(p)} {p['distanceKm']:.1f} km"
        + (" (in-network)" if p.get("inNetwork") else "")
        for p in provs
    ]
    result = f"{len(provs)} {specialty} providers found near you — " + ", ".join(facts)
    return ToolResult(
        result=result,
        args={"specialty": specialty, "geo": f"{lat},{lng}"},
        ok=True,
        facts=facts,
        data_source="real",
    )


def run(question: str, member_id: str, mode: str, base_url: str) -> ToolResult:
    if mode == "http":
        return _http(question, member_id, base_url)
    return _mock(question)
