"""POST /api/v1/gemini-live/speak — Gemini Live TTS for final ClaimVoice answers (C53).

Accepts the final answer text (post hallucination-guard) and returns playable
audio synthesised by Gemini Live.

Security
--------
- GEMINI_API_KEY stays server-side; never returned in the response.
- The endpoint only accepts short answer text (max 2000 chars).
- It returns a response shaped like TtsSynthesizeResponse so the existing
  browser speakAudio() path plays it with no protocol changes.

Flow
----
  POST { "text": "<final answer>" }
  → open Gemini Live session
  → session.speak_text(text)
  → collect PCM16 chunks
  → encode as WAV
  → return { ok: true, provider: "gemini-live", audioBase64: "...", mimeType: "audio/wav", ... }

On any failure (bridge unavailable, SDK missing, network error):
  → return { ok: false, fallback: "browser" }
"""

from __future__ import annotations

import base64
import struct
import io

from fastapi import APIRouter
from pydantic import BaseModel, Field

from voice_agent.lib.logger import logger
from voice_agent.streaming.gemini_live_bridge import build_gemini_bridge

router = APIRouter()

_SAMPLE_RATE = 24_000
_CHANNELS    = 1
_SAMPLE_WIDTH = 2  # PCM16 = 2 bytes per sample


class GeminiSpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class GeminiSpeakResponse(BaseModel):
    ok: bool
    provider: str = "gemini-live"
    voiceName: str = ""
    mimeType: str = ""
    audioBase64: str = ""
    reason: str = ""
    fallback: str = "browser"


def _pcm16_to_wav(pcm: bytes, sample_rate: int = _SAMPLE_RATE) -> bytes:
    """Wrap raw PCM16 LE bytes in a minimal WAV container."""
    num_samples  = len(pcm) // _SAMPLE_WIDTH
    byte_rate    = sample_rate * _CHANNELS * _SAMPLE_WIDTH
    block_align  = _CHANNELS * _SAMPLE_WIDTH
    data_size    = len(pcm)
    chunk_size   = 36 + data_size

    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", chunk_size))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH",
        16,           # subchunk1 size
        1,            # PCM format
        _CHANNELS,
        sample_rate,
        byte_rate,
        block_align,
        _SAMPLE_WIDTH * 8,  # bits per sample
    ))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(pcm)
    return buf.getvalue()


@router.post("/gemini-live/speak", response_model=GeminiSpeakResponse)
async def gemini_live_speak(req: GeminiSpeakRequest) -> GeminiSpeakResponse:
    bridge = build_gemini_bridge()

    if not bridge.is_available():
        logger.info("gemini_live_speak.unavailable")
        return GeminiSpeakResponse(
            ok=False,
            reason="Gemini Live not configured",
            fallback="browser",
        )

    pcm = b""
    try:
        async with bridge.open_session() as session:
            pcm = await session.speak_text(req.text)
    except Exception as exc:
        logger.warning("gemini_live_speak.session_error", error=str(exc))
        return GeminiSpeakResponse(
            ok=False,
            reason=f"session error: {type(exc).__name__}",
            fallback="browser",
        )

    if not pcm:
        logger.info("gemini_live_speak.empty_audio")
        return GeminiSpeakResponse(
            ok=False,
            reason="no audio returned from Gemini Live",
            fallback="browser",
        )

    wav = _pcm16_to_wav(pcm)
    audio_b64 = base64.b64encode(wav).decode()

    logger.info(
        "gemini_live_speak.success",
        text_chars=len(req.text),
        pcm_bytes=len(pcm),
        wav_bytes=len(wav),
    )

    return GeminiSpeakResponse(
        ok=True,
        provider="gemini-live",
        voiceName="Gemini Live",
        mimeType="audio/wav",
        audioBase64=audio_b64,
        reason="",
        fallback="browser",
    )
