from fastapi import APIRouter
from .members import router as members_router
from .plans import router as plans_router
from .formulary import router as formulary_router
from .coverage import router as coverage_router
from .cost import router as cost_router
from .formulary_lookup import router as formulary_lookup_router

router = APIRouter()
router.include_router(members_router)
router.include_router(plans_router)
router.include_router(formulary_router)
router.include_router(coverage_router)
router.include_router(cost_router)
router.include_router(formulary_lookup_router)
