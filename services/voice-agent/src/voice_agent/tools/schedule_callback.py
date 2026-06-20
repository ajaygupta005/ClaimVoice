"""schedule_callback tool — record a request for a human callback (internal/no-op)."""

from __future__ import annotations

from voice_agent.tools.schemas import ToolResult


def run(question: str = "", member_id: str = "", mode: str = "mock", base_url: str = "") -> ToolResult:
    return ToolResult(
        result="callback scheduled — a benefits specialist will call you back shortly",
        args={"member_id": member_id, "reason": question[:80]},
        ok=True,
        facts=[],
    )
