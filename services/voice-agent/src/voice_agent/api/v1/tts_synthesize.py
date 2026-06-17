"""
POST /api/v1/tts/synthesize

Synthesizes answer text to audio.
- If VOICE_AGENT_TTS_PROVIDER=google and credentials are available, uses Google Cloud TTS.
- Otherwise tries local macOS system TTS and returns a playable WAV blob.
- If no server-side TTS is available, returns ok=False so the browser can decide a fallback.
"""

from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from loguru import logger

from voice_agent.core.config import settings
from voice_agent.schemas.tts import TtsSynthesizeRequest, TtsSynthesizeResponse

router = APIRouter()


@router.post("/tts/synthesize", response_model=TtsSynthesizeResponse)
async def tts_synthesize(req: TtsSynthesizeRequest) -> JSONResponse:
    provider = settings.voice_agent_tts_provider

    if provider == "google":
        try:
            audio_b64, voice_name = _google_synthesize(req.text)
            return _audio_response(
                provider="google",
                voice_name=voice_name,
                mime_type="audio/mpeg",
                audio_b64=audio_b64,
            )
        except Exception as exc:
            logger.warning(f"Google TTS failed; trying system TTS fallback: {exc!r}")

    try:
        audio_b64, voice_name, mime_type = _system_synthesize(req.text)
        return _audio_response(
            provider="system",
            voice_name=voice_name,
            mime_type=mime_type,
            audio_b64=audio_b64,
        )
    except Exception as exc:
        logger.warning(f"System TTS unavailable: {exc!r}")
        return _unavailable_response(reason=f"system_error: {type(exc).__name__}")


def _audio_response(
    *,
    provider: Literal["google", "system"],
    voice_name: str,
    mime_type: str,
    audio_b64: str,
) -> JSONResponse:
    return JSONResponse(
        TtsSynthesizeResponse(
            ok=True,
            provider=provider,
            voiceName=voice_name,
            mimeType=mime_type,
            audioBase64=audio_b64,
        ).model_dump()
    )


def _unavailable_response(reason: str) -> JSONResponse:
    return JSONResponse(
        TtsSynthesizeResponse(
            ok=False,
            provider="system",
            reason=reason,
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


def _system_synthesize(text: str) -> tuple[str, str, str]:
    """Use macOS system TTS to produce a browser-playable WAV audio blob."""
    say_bin = shutil.which("say")
    if not say_bin:
        raise RuntimeError("system_tts_say_unavailable")

    afconvert_bin = shutil.which("afconvert")
    if not afconvert_bin:
        raise RuntimeError("system_tts_afconvert_unavailable")

    voice_name = settings.system_tts_voice_name.strip()

    with tempfile.TemporaryDirectory(prefix="claimvoice-tts-") as tmpdir:
        tmp = Path(tmpdir)
        aiff_path = tmp / "speech.aiff"
        wav_path = tmp / "speech.wav"

        say_cmd = [say_bin]
        if voice_name:
            say_cmd.extend(["-v", voice_name])
        say_cmd.extend(["-o", str(aiff_path), text])

        try:
            subprocess.run(
                say_cmd,
                check=True,
                capture_output=True,
                timeout=20,
            )
            used_voice = voice_name or "macOS default"
        except subprocess.CalledProcessError:
            fallback_cmd = [say_bin, "-o", str(aiff_path), text]
            subprocess.run(
                fallback_cmd,
                check=True,
                capture_output=True,
                timeout=20,
            )
            used_voice = "macOS default"

        subprocess.run(
            [afconvert_bin, "-f", "WAVE", "-d", "LEI16", str(aiff_path), str(wav_path)],
            check=True,
            capture_output=True,
            timeout=20,
        )

        audio_b64 = base64.b64encode(wav_path.read_bytes()).decode("utf-8")
        return audio_b64, used_voice, "audio/wav"
