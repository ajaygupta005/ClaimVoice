from fastapi import APIRouter
from .telephony_ws import router as telephony_ws_router
from .agent_respond import router as agent_respond_router

router = APIRouter()
router.include_router(telephony_ws_router)
router.include_router(agent_respond_router)
