from fastapi import APIRouter
from .telephony_ws import router as telephony_ws_router
from .agent_respond import router as agent_respond_router
from .tts_synthesize import router as tts_synthesize_router
from .runtime_status import router as runtime_status_router
from .readiness import router as readiness_router
from .gemini_live_ws import router as gemini_live_ws_router
from .gemini_live_speak import router as gemini_live_speak_router

router = APIRouter()
router.include_router(telephony_ws_router)
router.include_router(agent_respond_router)
router.include_router(tts_synthesize_router)
router.include_router(runtime_status_router)
router.include_router(readiness_router)
# Gemini routes are always registered so existing tests continue to work.
# When gemini_enabled=False the handlers themselves return graceful "unavailable"
# responses — Gemini just does not appear in runtime/status or UI.
router.include_router(gemini_live_ws_router)
router.include_router(gemini_live_speak_router)
