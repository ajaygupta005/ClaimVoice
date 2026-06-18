"""POST /api/v1/cost/estimate — copay / deductible / OOP estimate for a member."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from eligibility.lib.db import db_session
from eligibility.repositories.member_repo import get_cost_inputs
from eligibility.schemas.cost import CostEstimateRequest, CostEstimateResponse
from eligibility.services.cost_estimator import build_cost_estimate

router = APIRouter()


@router.post("/cost/estimate", response_model=CostEstimateResponse)
def cost_estimate(req: CostEstimateRequest) -> CostEstimateResponse:
    with db_session() as session:
        result = get_cost_inputs(session, req.memberId, req.service)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Member '{req.memberId}' not found")

    return build_cost_estimate(result, req.costType, req.service)
