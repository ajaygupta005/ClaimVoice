"""
POST /api/v1/tts/synthesize

Synthesizes answer text to audio.
- If VOICE_AGENT_TTS_PROVIDER=cartesia, calls Cartesia /tts/bytes (HTTP, no SDK).
- If VOICE_AGENT_TTS_PROVIDER=google and credentials are available, uses Google Cloud TTS.
- Otherwise tries local macOS system TTS and returns a playable WAV blob.
- If no server-side TTS is available, returns ok=False so the browser can decide a fallback.
"""

from __future__ import annotations

import base64
import io
import shutil
import subprocess
import tempfile
import time
import wave
from pathlib import Path
from typing import Literal

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from voice_agent.core.config import settings
from voice_agent.lib.logger import logger
from voice_agent.schemas.tts import TtsSynthesizeRequest, TtsSynthesizeResponse

router = APIRouter()

_CARTESIA_API_URL = "https://api.cartesia.ai/tts/bytes"
_CARTESIA_API_VERSION = "2026-03-01"
_CARTESIA_MAX_CHARS = 2_000
_CARTESIA_TIMEOUT_S = 45.0


class _CartesiaError(RuntimeError):
    """Cartesia-specific failure with a machine-readable error code."""
    def __init__(self, error_code: str, detail: str = "") -> None:
        super().__init__(detail or error_code)
        self.error_code = error_code


@router.post("/tts/synthesize", response_model=TtsSynthesizeResponse)
async def tts_synthesize(req: TtsSynthesizeRequest) -> JSONResponse:
    provider = settings.voice_agent_tts_provider
    primary_error_code = ""

    if provider == "cartesia":
        try:
            audio_b64, voice_name = _cartesia_synthesize(req.text)
            return _audio_response(
                provider="cartesia",
                voice_name=voice_name,
                mime_type="audio/wav",
                audio_b64=audio_b64,
            )
        except _CartesiaError as exc:
            primary_error_code = exc.error_code
            logger.warning("cartesia_tts.fallback", reason=exc.error_code)
        except Exception as exc:
            primary_error_code = "cartesia_error"
            logger.warning("cartesia_tts.fallback", reason=str(exc))

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
            logger.warning("google_tts.fallback", reason=str(exc))

    try:
        audio_b64, voice_name, mime_type = _system_synthesize(req.text)
        return _audio_response(
            provider="system",
            voice_name=voice_name,
            mime_type=mime_type,
            audio_b64=audio_b64,
        )
    except Exception as exc:
        logger.warning("system_tts.unavailable", reason=str(exc))
        error_code = primary_error_code or f"system_error_{type(exc).__name__}"
        return _unavailable_response(reason=str(exc), error_code=error_code)


def _audio_response(
    *,
    provider: Literal["cartesia", "google", "system"],
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


def _unavailable_response(reason: str, error_code: str = "") -> JSONResponse:
    return JSONResponse(
        TtsSynthesizeResponse(
            ok=False,
            provider="system",
            reason=reason,
            errorCode=error_code or reason,
            fallback="browser",
        ).model_dump(),
        status_code=200,
    )


def _cartesia_synthesize(text: str) -> tuple[str, str]:
    """Call Cartesia /tts/bytes directly (HTTP, no SDK) and return (base64_wav, voice_name)."""
    if not settings.cartesia_api_key:
        raise _CartesiaError("cartesia_key_missing")

    if len(text) > _CARTESIA_MAX_CHARS:
        text = text[:_CARTESIA_MAX_CHARS]

    payload = {
        "model_id": settings.cartesia_tts_model,
        "transcript": text,
        "voice": {
            "mode": "id",
            "id": settings.cartesia_voice_id,
        },
        "output_format": {
            "container": settings.cartesia_tts_container,
            "encoding": settings.cartesia_tts_encoding,
            "sample_rate": settings.cartesia_tts_sample_rate,
        },
        "language": settings.cartesia_tts_language,
        "generation_config": {
            "speed": settings.cartesia_tts_speed,
            "volume": settings.cartesia_tts_volume,
        },
    }

    voice_id_suffix = settings.cartesia_voice_id[-8:] if settings.cartesia_voice_id else "unknown"
    t0 = time.monotonic()
    logger.info(
        "cartesia_tts.request",
        model=settings.cartesia_tts_model,
        voice_name=settings.cartesia_voice_name,
        voice_id_suffix=voice_id_suffix,
        text_len=len(text),
    )

    try:
        resp = httpx.post(
            _CARTESIA_API_URL,
            headers={
                "Cartesia-Version": _CARTESIA_API_VERSION,
                "X-API-Key": settings.cartesia_api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=_CARTESIA_TIMEOUT_S,
        )
    except httpx.TimeoutException as exc:
        logger.warning("cartesia_tts.timeout", error=str(exc))
        raise _CartesiaError("cartesia_timeout") from exc
    except httpx.RequestError as exc:
        logger.warning("cartesia_tts.request_error", error=str(exc))
        raise _CartesiaError("cartesia_request_error", str(exc)) from exc

    if resp.status_code != 200:
        logger.warning("cartesia_tts.http_error", status=resp.status_code)
        raise _CartesiaError(f"cartesia_http_{resp.status_code}")

    audio_bytes = resp.content
    if not audio_bytes:
        raise _CartesiaError("cartesia_empty_audio")

    latency_ms = int((time.monotonic() - t0) * 1000)
    logger.info(
        "cartesia_tts.done",
        latency_ms=latency_ms,
        audio_bytes=len(audio_bytes),
        voice_name=settings.cartesia_voice_name,
    )

    # Cartesia returns a complete WAV when container=wav — base64-encode directly.
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    return audio_b64, settings.cartesia_voice_name


def _pcm16_to_wav(pcm: bytes, *, sample_rate: int) -> bytes:
    """Wrap mono PCM16 little-endian bytes in a WAV container."""
    out = io.BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return out.getvalue()


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
