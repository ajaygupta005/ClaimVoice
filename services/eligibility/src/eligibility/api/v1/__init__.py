from fastapi import APIRouter
from .members import router as members_router
from .plans import router as plans_router
from .formulary import router as formulary_router

router = APIRouter()
router.include_router(members_router)
router.include_router(plans_router)
router.include_router(formulary_router)
