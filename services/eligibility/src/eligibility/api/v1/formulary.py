"""GET /api/v1/formulary/search"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query

from eligibility.lib.db import db_session
from eligibility.repositories.member_repo import search_formulary
from eligibility.schemas.formulary import FormularyDrugOut, FormularySearchResponse

router = APIRouter()


@router.get("/formulary/search", response_model=FormularySearchResponse)
def formulary_search(
    planId: uuid.UUID = Query(..., description="Plan UUID"),
    q: str = Query(..., min_length=1, description="Drug name search term"),
    limit: int = Query(20, ge=1, le=100),
) -> FormularySearchResponse:
    with db_session() as session:
        rows = search_formulary(session, planId, q, limit)

    drugs = [
        FormularyDrugOut(
            id=r["id"],
            drugName=r["drug_name"],
            ndcCode=r.get("ndc_code"),
            formularyTier=r.get("formulary_tier"),
            priorAuthRequired=bool(r.get("prior_auth_required", False)),
            stepTherapyRequired=bool(r.get("step_therapy_required", False)),
            quantityLimit=r.get("quantity_limit"),
        )
        for r in rows
    ]
    return FormularySearchResponse(planId=planId, query=q, drugs=drugs)
