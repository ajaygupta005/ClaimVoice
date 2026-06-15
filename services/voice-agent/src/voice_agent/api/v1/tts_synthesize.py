"""
POST /api/v1/tts/synthesize

Synthesizes answer text to audio.
- If VOICE_AGENT_TTS_PROVIDER=google and credentials are available, uses Google Cloud TTS.
- Otherwise returns TtsUnavailableResponse so the browser can fall back to speechSynthesis.
"""

from __future__ import annotations

import base64

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from loguru import logger

from voice_agent.core.config import settings
from voice_agent.schemas.tts import TtsSynthesizeRequest, TtsSynthesizeResponse

router = APIRouter()


@router.post("/tts/synthesize", response_model=TtsSynthesizeResponse)
async def tts_synthesize(req: TtsSynthesizeRequest) -> JSONResponse:
    if settings.voice_agent_tts_provider != "google":
        return JSONResponse(
            TtsSynthesizeResponse(
                ok=False,
                provider="google",
                reason="tts_provider_not_google",
                fallback="browser",
            ).model_dump(),
            status_code=200,
        )

    try:
        audio_b64, voice_name = _google_synthesize(req.text)
        return JSONResponse(
            TtsSynthesizeResponse(
                ok=True,
                provider="google",
                voiceName=voice_name,
                mimeType="audio/mpeg",
                audioBase64=audio_b64,
            ).model_dump()
        )
    except Exception as exc:
        logger.warning(f"Google TTS failed: {exc!r}")
        return JSONResponse(
            TtsSynthesizeResponse(
                ok=False,
                provider="google",
                reason=f"google_error: {type(exc).__name__}",
                fallback="browser",
            ).model_dump(),
            status_code=200,
        )


def _google_synthesize(text: str) -> tuple[str, str]:
    """Call Google Cloud TTS and return (base64_audio, voice_name)."""
    from google.cloud import texttospeech  # type: ignore[import-untyped]

    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code=settings.google_tts_language_code,
        name=settings.google_tts_voice_name,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
    )
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )
    audio_b64 = base64.b64encode(response.audio_content).decode("utf-8")
    return audio_b64, settings.google_tts_voice_name
