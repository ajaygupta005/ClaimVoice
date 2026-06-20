from fastapi import APIRouter
from .telephony_ws import router as telephony_ws_router
from .agent_respond import router as agent_respond_router
from .tts_synthesize import router as tts_synthesize_router
from .runtime_status import router as runtime_status_router
from .gemini_live_ws import router as gemini_live_ws_router

router = APIRouter()
router.include_router(telephony_ws_router)
router.include_router(agent_respond_router)
router.include_router(tts_synthesize_router)
router.include_router(runtime_status_router)
router.include_router(gemini_live_ws_router)
