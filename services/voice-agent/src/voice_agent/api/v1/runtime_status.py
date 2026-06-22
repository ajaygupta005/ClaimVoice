"""GET /api/v1/runtime/status — safe voice runtime metadata (Component 50/71).

Returns only non-secret fields. GEMINI_API_KEY and CARTESIA_API_KEY are never included.
RAG readiness fields are fetched from the eligibility service (Component 71).
"""

from __future__ import annotations

import importlib
import urllib.error
import urllib.request
from typing import Any, Literal

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

RagStatusKind = Literal["ready", "key_missing", "table_missing", "empty", "no_plan_links", "db_error", "unreachable"]


class VoiceRuntimeStatus(BaseModel):
    runtime: VoiceRuntimeKind
    model: str
    voice: str
    note: str
    tts_provider: str = ""    # "cartesia", "google", "system", "browser"
    tts_voice_name: str = ""  # display name, e.g. "Skylar"
    # RAG readiness (Component 71) — populated from eligibility service, never fatal
    rag_status: RagStatusKind = "unreachable"
    rag_reason: str = ""
    rag_chunks_count: int = 0
    voyage_configured: bool = False
    pgvector_available: bool = False


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


def _fetch_rag_readiness() -> dict[str, Any]:
    """Fetch RAG readiness from the eligibility service. Never raises — returns unreachable on error."""
    base_url = settings.eligibility_base_url.rstrip("/")
    url = f"{base_url}/api/v1/rag/readiness"
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            import json
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
        return {
            "rag_status": body.get("ragStatus", "unreachable"),
            "rag_reason": body.get("ragReason", ""),
            "rag_chunks_count": int(body.get("sbcChunksCount", 0)),
            "voyage_configured": bool(body.get("voyageConfigured", False)),
            "pgvector_available": bool(body.get("pgvectorAvailable", False)),
        }
    except Exception:
        return {
            "rag_status": "unreachable",
            "rag_reason": "eligibility service not reachable",
            "rag_chunks_count": 0,
            "voyage_configured": False,
            "pgvector_available": False,
        }


def _resolve_runtime() -> VoiceRuntimeStatus:
    requested = settings.claimvoice_voice_runtime
    tts = _tts_fields()
    rag = _fetch_rag_readiness()

    # Gemini Live is only active when explicitly enabled via GEMINI_ENABLED=true.
    # Without the flag, the normal demo path is Claude + Cartesia only.
    if requested == "gemini-live" and settings.gemini_enabled:
        if settings.gemini_api_key:
            if not _gemini_sdk_available():
                return VoiceRuntimeStatus(
                    runtime="gemini-live-unavailable",
                    model=settings.gemini_live_model,
                    voice=settings.gemini_live_voice,
                    note="google-genai SDK missing — falling back to browser voice.",
                    **tts,
                    **rag,
                )
            return VoiceRuntimeStatus(
                runtime="gemini-live-configured",
                model=settings.gemini_live_model,
                voice=settings.gemini_live_voice,
                note="Gemini Live key present. Bridge not yet active.",
                **tts,
                **rag,
            )
        return VoiceRuntimeStatus(
            runtime="gemini-live-unavailable",
            model=settings.gemini_live_model,
            voice=settings.gemini_live_voice,
            note="GEMINI_API_KEY missing — falling back to browser voice.",
            **tts,
            **rag,
        )

    return VoiceRuntimeStatus(
        runtime="browser",
        model="",
        voice="",
        note="Using browser Web Speech API.",
        **tts,
        **rag,
    )


@router.get("/runtime/status", response_model=VoiceRuntimeStatus)
def get_runtime_status() -> VoiceRuntimeStatus:
    return _resolve_runtime()
