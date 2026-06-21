"""GET /api/v1/runtime/status — safe voice runtime metadata (Component 50).

Returns only non-secret fields. GEMINI_API_KEY and CARTESIA_API_KEY are never included.
"""

from __future__ import annotations

import importlib
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from voice_agent.core.config import settings

router = APIRouter()

VoiceRuntimeKind = Literal[
    "browser",
    "gemini-live-configured",
    "gemini-live-unavailable",
    "fallback",
]


class VoiceRuntimeStatus(BaseModel):
    runtime: VoiceRuntimeKind
    model: str
    voice: str
    note: str
    tts_provider: str = ""    # "cartesia", "google", "system", "browser"
    tts_voice_name: str = ""  # display name, e.g. "Skylar"


def _gemini_sdk_available() -> bool:
    try:
        importlib.import_module("google.genai")
    except ImportError:
        return False
    return True


def _tts_fields() -> dict[str, str]:
    provider = settings.voice_agent_tts_provider
    voice_name = settings.cartesia_voice_name if provider == "cartesia" else ""
    return {"tts_provider": provider, "tts_voice_name": voice_name}


def _resolve_runtime() -> VoiceRuntimeStatus:
    requested = settings.claimvoice_voice_runtime
    tts = _tts_fields()

    if requested == "gemini-live":
        if settings.gemini_api_key:
            if not _gemini_sdk_available():
                return VoiceRuntimeStatus(
                    runtime="gemini-live-unavailable",
                    model=settings.gemini_live_model,
                    voice=settings.gemini_live_voice,
                    note="google-genai SDK missing — falling back to browser voice.",
                    **tts,
                )
            return VoiceRuntimeStatus(
                runtime="gemini-live-configured",
                model=settings.gemini_live_model,
                voice=settings.gemini_live_voice,
                note="Gemini Live key present. Bridge not yet active.",
                **tts,
            )
        return VoiceRuntimeStatus(
            runtime="gemini-live-unavailable",
            model=settings.gemini_live_model,
            voice=settings.gemini_live_voice,
            note="GEMINI_API_KEY missing — falling back to browser voice.",
            **tts,
        )

    return VoiceRuntimeStatus(
        runtime="browser",
        model="",
        voice="",
        note="Using browser Web Speech API.",
        **tts,
    )


@router.get("/runtime/status", response_model=VoiceRuntimeStatus)
def get_runtime_status() -> VoiceRuntimeStatus:
    return _resolve_runtime()
