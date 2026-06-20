"""GET /api/v1/runtime/status — safe voice runtime metadata (Component 50).

Returns only non-secret fields. GEMINI_API_KEY is never included.
"""

from __future__ import annotations

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


def _resolve_runtime() -> VoiceRuntimeStatus:
    requested = settings.claimvoice_voice_runtime

    if requested == "gemini-live":
        if settings.gemini_api_key:
            return VoiceRuntimeStatus(
                runtime="gemini-live-configured",
                model=settings.gemini_live_model,
                voice=settings.gemini_live_voice,
                note="Gemini Live key present. Bridge not yet active.",
            )
        return VoiceRuntimeStatus(
            runtime="gemini-live-unavailable",
            model=settings.gemini_live_model,
            voice=settings.gemini_live_voice,
            note="GEMINI_API_KEY missing — falling back to browser voice.",
        )

    return VoiceRuntimeStatus(
        runtime="browser",
        model="",
        voice="",
        note="Using browser Web Speech API.",
    )


@router.get("/runtime/status", response_model=VoiceRuntimeStatus)
def get_runtime_status() -> VoiceRuntimeStatus:
    return _resolve_runtime()
