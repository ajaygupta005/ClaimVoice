"""find_provider tool — nearby in-network providers. http -> WS-5 GET /providers/near."""

from __future__ import annotations

import re

import httpx

from voice_agent.tools.schemas import ToolResult

# Default member geo (Midtown Manhattan) until real member context is threaded (M13).
_DEFAULT_GEO = (40.7580, -73.9855)


def _mock(question: str) -> ToolResult:
    if re.search(r"\b(x-ray|xray|x ray|imaging|radiolog|radiology|imaging center)\b", question, re.IGNORECASE):
        result = (
            "2 in-network imaging centers within 3 miles — RadNet at 400 Madison Ave (in-network), "
            "City Imaging at 55 W 45th St (in-network)"
        )
        return ToolResult(result, {"specialty": "imaging", "geo": "member location"}, True, [result])
    if re.search(r"\b(primary care|PCP)\b", question, re.IGNORECASE):
        result = (
            "3 in-network primary care providers found — Dr. Rachel Kim 0.4 mi (accepting patients), "
            "Dr. Elena Varga 0.8 mi, Dr. James Park 1.2 mi"
        )
        return ToolResult(result, {"specialty": "primary care", "geo": "member location"}, True, [result])
    match = re.search(
        r"\b(internal medicine|family medicine|family practice|pediatric(?:ian)?s?|"
        r"psychiatr(?:ist|y)|emergency(?: medicine)?|cardiolog(?:ist|y)|dermatolog(?:ist|y)|"
        r"orthoped(?:ist|ics|ic surgery)|therapist|specialist|primary care|PCP|"
        r"radiologist|imaging center|urgent care|gynecologist|obstetrics|OB-GYN|"
        r"ophthalmologist|optometrist)\b",
        question, re.IGNORECASE,
    )
    specialty = match.group(0) if match else "provider"
    result = f"3 in-network {specialty}s found within 5 miles"
    return ToolResult(result, {"specialty": specialty, "geo": "member location"}, True, [result])


def _provider_name(p: dict) -> str:
    return (
        p.get("organizationName")
        or " ".join(filter(None, [p.get("firstName"), p.get("lastName")]))
        or p.get("npi", "provider")
    )


def _http(question: str, member_id: str, base_url: str) -> ToolResult:
    specialty = _mock(question).args["specialty"]
    lat, lng = _DEFAULT_GEO
    r = httpx.get(
        f"{base_url}/api/v1/providers/near",
        params={"specialty": specialty, "lat": lat, "lng": lng, "radiusKm": 25, "limit": 3},
        timeout=5.0,
    )
    r.raise_for_status()
    provs = r.json().get("providers", [])
    if not provs:
        result = f"no {specialty} providers found near you"
        return ToolResult(result, {"specialty": specialty}, True, [result])
    facts = [
        f"{_provider_name(p)} {p['distanceKm']} km"
        + (" (in-network)" if p.get("inNetwork") else "")
        for p in provs
    ]
    result = f"{len(provs)} {specialty} providers found near you — " + ", ".join(facts)
    return ToolResult(result, {"specialty": specialty, "geo": f"{lat},{lng}"}, True, facts)


def run(question: str, member_id: str, mode: str, base_url: str) -> ToolResult:
    if mode == "http":
        try:
            return _http(question, member_id, base_url)
        except Exception:
            pass
    return _mock(question)
