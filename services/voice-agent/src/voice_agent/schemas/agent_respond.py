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
    data_source: str = "demo"   # "real" | "demo" | "error"
    error_code: str = ""
    member_source: str = ""     # "provided" | "demo" | "missing"


# ── Pipeline event contract (Component 63) ────────────────────────────────────

class PipelineStage(BaseModel):
    name: str      # "identify" | "understand" | "tool" | "guard" | "respond"
    status: str    # "ok" | "error" | "escalated" | "demo"
    detail: str = ""


class PipelineToolCall(BaseModel):
    tool: str
    data_source: str    # "real" | "demo" | "error"
    error_code: str = ""
    result_summary: str  # first 120 chars of result
    ok: bool


class PipelineGuard(BaseModel):
    passed: bool
    reason: str


class PipelineAnswer(BaseModel):
    source: str    # "claude" | "mock" | "escalated" | "tool_error"
    grounded: bool


class PipelineSummary(BaseModel):
    turn_id: str            # uuid4 hex
    intent: str
    member_source: str      # "provided" | "demo" | "missing"
    tool_mode: str          # "mock" | "http"
    stages: list[PipelineStage]
    tools: list[PipelineToolCall]
    guard: PipelineGuard
    answer: PipelineAnswer
    error: str = ""         # non-empty only when the pipeline itself failed


class RagMetaItem(BaseModel):
    """RAG retrieval + guard metadata in HTTP responses (Component 68/69)."""
    ragAttempted: bool = False
    ragAvailable: bool = False
    ragChunksCount: int = 0
    ragFallbackReason: str = ""
    ragSource: str = ""
    # Guard fields (Component 69)
    guardPassed: bool = False
    guardReasonCode: str = ""
    supportedBy: list[str] = []
    unsupportedClaims: list[str] = []
    ragFactsUsed: int = 0


class EvidenceItem(BaseModel):
    """Single SBC evidence citation surfaced to the UI (Component 70).

    Only safe display fields — no backend credentials or raw embeddings.
    """
    text: str           # chunk text (max 400 chars)
    sectionName: str
    sourceFile: str
    distance: float


class AgentRespondResponse(BaseModel):
    question: str
    answer: str
    intent: str
    grounded: bool
    guard_reason: str
    tool_trace: list[ToolTraceItem]
    composer_mode: str          # "mock" | "claude"
    tool_mode: str              # "mock" | "http"
    member_source: str          # "provided" | "demo" | "missing"
    backend_statuses: list[dict[str, str]]
    pipeline: PipelineSummary
    rag: RagMetaItem = RagMetaItem()
    evidence: list[EvidenceItem] = []   # Component 70: SBC citations for UI
