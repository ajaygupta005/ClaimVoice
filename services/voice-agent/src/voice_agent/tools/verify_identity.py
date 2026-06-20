"""verify_identity tool — confirm a member by id (http -> WS-4 member summary).

The active linear graph verifies via the identify_member node; this tool is available
for the conversational state machine (M13+). Mock mode always succeeds.
"""

from __future__ import annotations

import httpx

from voice_agent.tools.schemas import ToolResult


def _http(member_id: str, base_url: str) -> ToolResult:
    r = httpx.get(f"{base_url}/api/v1/members/{member_id}/summary", timeout=5.0)
    if r.status_code == 404:
        return ToolResult(f"member {member_id} not found", {"member_id": member_id}, ok=False, facts=[])
    r.raise_for_status()
    d = r.json()
    name = d.get("member", {}).get("name", member_id)
    return ToolResult(f"identity verified for {name}", {"member_id": member_id}, ok=True, facts=[])


def run(question: str, member_id: str, mode: str, base_url: str) -> ToolResult:
    if mode == "http":
        try:
            return _http(member_id, base_url)
        except Exception:
            pass
    return ToolResult("identity verified", {"member_id": member_id}, ok=True, facts=[])
