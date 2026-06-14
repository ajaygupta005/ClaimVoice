from fastapi import APIRouter
from .providers import router as providers_router

router = APIRouter()
router.include_router(providers_router)
