from fastapi import APIRouter
from .telephony_ws import router as telephony_ws_router

router = APIRouter()
router.include_router(telephony_ws_router)
