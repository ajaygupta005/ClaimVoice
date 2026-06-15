"""
TTS audio event schemas.

Wire format (JSON over WebSocket):

  {
    "type": "tts.audio",
    "callSid": "CA...",
    "streamSid": "SM...",
    "chunkIndex": 0,
    "totalChunks": 2,
    "isFinal": false,
    "pcm24k": "<base64 PCM16 24 kHz>"
  }

  {
    "type": "tts.error",
    "callSid": "CA...",
    "streamSid": "SM...",
    "reason": "empty_text"
  }

`pcm24k` is base64-encoded PCM16 little-endian at 24 000 Hz, 1 channel.
The telephony service re-samples to 8 kHz µ-law before sending to Twilio.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class TtsAudioEvent(BaseModel):
    type: Literal["tts.audio"] = "tts.audio"
    callSid: str
    streamSid: str
    chunkIndex: int
    totalChunks: int
    isFinal: bool
    pcm24k: str  # base64-encoded PCM16 24 kHz


class TtsErrorEvent(BaseModel):
    type: Literal["tts.error"] = "tts.error"
    callSid: str
    streamSid: str
    reason: str


# ---------------------------------------------------------------------------
# HTTP endpoint schemas (Component 38)
# ---------------------------------------------------------------------------

from pydantic import Field  # noqa: E402


class TtsSynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    voice: str = "default"
    format: Literal["mp3", "wav"] = "mp3"


class TtsSynthesizeResponse(BaseModel):
    """Unified response — always returned as 200 so the browser can branch on ok."""
    ok: bool
    provider: Literal["google", "browser"]
    voiceName: str = ""
    mimeType: str = ""
    audioBase64: str = ""
    reason: str = ""          # set when ok=False
    fallback: str = "browser" # set when ok=False
