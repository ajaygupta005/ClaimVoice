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


class AnswerFinalEvent(BaseModel):
    type: Literal["answer.final"] = "answer.final"
    callSid: str
    streamSid: str
    intent: str
    text: str
    grounded: bool
    tool_trace: list[ToolTrace]
