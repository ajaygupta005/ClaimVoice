"""GET /api/v1/formulary/lookup — best drug match + alternatives for a member."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from eligibility.lib.db import db_session
from eligibility.repositories.member_repo import lookup_drug
from eligibility.schemas.formulary import FormularyLookupResponse
from eligibility.services.formulary import build_formulary_lookup

router = APIRouter()


@router.get("/formulary/lookup", response_model=FormularyLookupResponse)
def formulary_lookup(
    memberId: str = Query(..., min_length=1),
    drug: str = Query(..., min_length=1),
    limit: int = Query(5, ge=1, le=25),
) -> FormularyLookupResponse:
    with db_session() as session:
        result = lookup_drug(session, memberId, drug, limit)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Member '{memberId}' not found")

    return build_formulary_lookup(memberId, result, drug)
