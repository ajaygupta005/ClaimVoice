"""escalate tool — hand off to a human when intent is unclear or out of scope."""

from __future__ import annotations

from voice_agent.tools.schemas import ToolResult


def run(question: str = "", member_id: str = "", mode: str = "mock", base_url: str = "") -> ToolResult:
    return ToolResult(
        result="escalated — intent unclear or outside AI scope",
        args={"reason": "intent unclear"},
        ok=False,
        facts=[],
    )
