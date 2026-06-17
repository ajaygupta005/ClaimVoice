"""
Pydantic schemas for bridge events sent by the telephony service (Component 23).

Event wire format (JSON over WebSocket):

  { "type": "start", "callSid": "...", "streamSid": "...", "mediaFormat": {...} }
  { "type": "audio", "callSid": "...", "streamSid": "...", "pcm24k": "<base64>" }
  { "type": "stop",  "callSid": "...", "streamSid": "..." }

Responses sent back to the caller:

  { "ack": "start",  "callSid": "...", "streamSid": "..." }
  { "ack": "audio",  "callSid": "...", "streamSid": "...", "bytes": <int> }
  { "ack": "stop",   "callSid": "...", "streamSid": "..." }
  { "error": "...",  "detail": "..." }
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Union
import base64

from pydantic import BaseModel, Field, field_validator


# ── Inbound event schemas ─────────────────────────────────────────────────────

class MediaFormat(BaseModel):
    encoding: str
    sampleRate: int
    channels: int


class StartEvent(BaseModel):
    type: Literal["start"]
    callSid: str
    streamSid: str
    mediaFormat: Optional[MediaFormat] = None


class AudioEvent(BaseModel):
    type: Literal["audio"]
    callSid: str
    streamSid: str
    pcm24k: str  # base64-encoded PCM16 24 kHz

    @field_validator("pcm24k")
    @classmethod
    def must_be_valid_base64(cls, v: str) -> str:
        try:
            base64.b64decode(v, validate=True)
        except Exception as exc:
            raise ValueError("pcm24k must be valid base64") from exc
        return v

    def decode_pcm(self) -> bytes:
        return base64.b64decode(self.pcm24k)


class StopEvent(BaseModel):
    type: Literal["stop"]
    callSid: str
    streamSid: str


BridgeEvent = Annotated[
    Union[StartEvent, AudioEvent, StopEvent],
    Field(discriminator="type"),
]


# ── Outbound response schemas ─────────────────────────────────────────────────

class AckResponse(BaseModel):
    ack: str
    callSid: str
    streamSid: str
    bytes: Optional[int] = None  # only present on audio ack


class ErrorResponse(BaseModel):
    error: str
    detail: str
