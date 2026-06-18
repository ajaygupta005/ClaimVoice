"""POST /api/v1/providers/bulk — batch provider lookup by NPI list."""

from __future__ import annotations

from fastapi import APIRouter

from providers.lib.db import db_session
from providers.repositories.provider_repo import get_providers_by_npis
from providers.schemas.provider import ProviderBulkRequest, ProviderBulkResponse

from .providers import _row_to_provider

router = APIRouter()


@router.post("/providers/bulk", response_model=ProviderBulkResponse)
def providers_bulk(req: ProviderBulkRequest) -> ProviderBulkResponse:
    with db_session() as session:
        rows = get_providers_by_npis(session, req.npis)
    return ProviderBulkResponse(providers=[_row_to_provider(r) for r in rows])
