"""Request/response schemas for POST /api/v1/agent/respond."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentRespondRequest(BaseModel):
    question: str = Field(..., min_length=1)
    memberId: str = "CVX-0042-MT"
    source: Literal["typed", "voice", "demo"] = "typed"
    # Optional stable id to carry conversation memory across turns.
    sessionId: str | None = None


class ToolTraceItem(BaseModel):
    tool: str
    args: dict[str, Any]
    result: str
    ok: bool


class AgentRespondResponse(BaseModel):
    question: str
    answer: str
    intent: str
    grounded: bool
    guard_reason: str
    tool_trace: list[ToolTraceItem]
    composer_mode: str          # "mock" | "claude"
    backend_statuses: list[dict[str, str]]
