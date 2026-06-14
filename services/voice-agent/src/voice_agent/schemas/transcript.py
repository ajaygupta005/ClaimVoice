"""
Transcript event schemas emitted by the STT adapter.

Wire format (JSON over WebSocket):

  {
    "type": "transcript.partial",
    "callSid": "CA...",
    "streamSid": "SM...",
    "text": "is an MRI",
    "confidence": 0.82
  }

  {
    "type": "transcript.final",
    "callSid": "CA...",
    "streamSid": "SM...",
    "text": "Is an MRI of the brain covered?",
    "confidence": 0.91,
    "duration_ms": 4200
  }
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class PartialTranscriptEvent(BaseModel):
    type: Literal["transcript.partial"] = "transcript.partial"
    callSid: str
    streamSid: str
    text: str
    confidence: float = Field(ge=0.0, le=1.0)


class FinalTranscriptEvent(BaseModel):
    type: Literal["transcript.final"] = "transcript.final"
    callSid: str
    streamSid: str
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    duration_ms: Optional[int] = None  # total audio duration that produced this transcript
