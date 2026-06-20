"""GET /api/v1/coverage — structured coverage lookup for a member + service."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from eligibility.lib.db import db_session
from eligibility.repositories.member_repo import get_coverage
from eligibility.schemas.coverage import CoverageResponse
from eligibility.services.coverage import build_coverage_response

router = APIRouter()


@router.get("/coverage", response_model=CoverageResponse)
def coverage(
    memberId: str = Query(..., min_length=1),
    service: str = Query(..., min_length=1),
    networkType: str = Query("In Network"),
) -> CoverageResponse:
    with db_session() as session:
        result = get_coverage(session, memberId, service, networkType)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Member '{memberId}' not found")

    return build_coverage_response(result, service, networkType)
