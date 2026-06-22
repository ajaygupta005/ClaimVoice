from fastapi import APIRouter
from .members import router as members_router
from .plans import router as plans_router
from .formulary import router as formulary_router
from .coverage import router as coverage_router
from .cost import router as cost_router
from .formulary_lookup import router as formulary_lookup_router
from .fact_check import router as fact_check_router
from .sbc_rag import router as sbc_rag_router
from .rag_readiness import router as rag_readiness_router

router = APIRouter()
router.include_router(members_router)
router.include_router(plans_router)
router.include_router(formulary_router)
router.include_router(coverage_router)
router.include_router(cost_router)
router.include_router(formulary_lookup_router)
router.include_router(fact_check_router)
router.include_router(sbc_rag_router)
router.include_router(rag_readiness_router)
