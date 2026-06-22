"""
Answer orchestrator event schemas.

Wire format (JSON over WebSocket):

  {
    "type": "answer.final",
    "callSid": "CA...",
    "streamSid": "SM...",
    "intent": "coverage",
    "text": "Yes, MRI is covered. Since you have not met your deductible ...",
    "grounded": true,
    "tool_trace": [
      { "tool": "check_coverage", "args": {"service": "MRI"}, "result": "covered", "ok": true }
    ]
  }

The `grounded` flag is `true` when the answer is derived from a successful
tool call, `false` when the answer falls back to an escalation response.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class ToolTrace(BaseModel):
    tool: str
    args: dict[str, Any]
    result: str
    ok: bool
    data_source: str = "demo"   # "real" | "demo" | "error"
    error_code: str = ""
    member_source: str = ""     # "provided" | "demo" | "missing"


class RagMeta(BaseModel):
    """RAG retrieval + guard metadata (Component 68/69). Present on every answer."""
    ragAttempted: bool = False
    ragAvailable: bool = False
    ragChunksCount: int = 0
    ragFallbackReason: str = ""
    ragSource: str = ""
    # Guard fields (Component 69)
    guardPassed: bool = False
    guardReasonCode: str = ""        # supported_by_structured_tool | supported_by_sbc_rag |
                                     #   unsupported_claim | no_facts_available | rag_unavailable
    supportedBy: list[str] = []      # ["structured_tool"] | ["sbc_rag"] | both
    unsupportedClaims: list[str] = []
    ragFactsUsed: int = 0


class AnswerFinalEvent(BaseModel):
    type: Literal["answer.final"] = "answer.final"
    callSid: str
    streamSid: str
    intent: str
    text: str
    grounded: bool
    tool_trace: list[ToolTrace]
    rag: RagMeta = RagMeta()
    rag_chunks: list[dict[str, Any]] = []   # Component 70: raw chunks for evidence UI
