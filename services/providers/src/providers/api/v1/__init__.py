from fastapi import APIRouter
from .providers import router as providers_router
from .providers_near import router as providers_near_router
from .providers_bulk import router as providers_bulk_router

router = APIRouter()
# Register /providers/near and /providers/bulk BEFORE /providers/{npi} so the static
# paths are not shadowed by the dynamic detail route.
router.include_router(providers_near_router)
router.include_router(providers_bulk_router)
router.include_router(providers_router)
