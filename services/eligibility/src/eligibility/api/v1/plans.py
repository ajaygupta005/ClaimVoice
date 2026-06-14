"""GET /api/v1/plans/{plan_id}/benefits"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from eligibility.lib.db import db_session
from eligibility.repositories.member_repo import get_plan_benefits
from eligibility.schemas.benefit import BenefitOut, BenefitsResponse

router = APIRouter()


@router.get("/plans/{plan_id}/benefits", response_model=BenefitsResponse)
def plan_benefits(plan_id: uuid.UUID) -> BenefitsResponse:
    with db_session() as session:
        rows = get_plan_benefits(session, plan_id)

    benefits = [
        BenefitOut(
            id=r["id"],
            benefitName=r.get("benefit_name"),
            serviceCategory=r.get("service_category"),
            networkType=r.get("network_type"),
            individualDeductibleCents=r.get("individual_deductible_cents"),
            familyDeductibleCents=r.get("family_deductible_cents"),
            copayAmountCents=r.get("copay_amount_cents"),
            coinsurancePercentage=float(r["coinsurance_percentage"]) if r.get("coinsurance_percentage") is not None else None,
            outOfPocketMaxCents=r.get("out_of_pocket_max_cents"),
            requiresPriorAuth=bool(r.get("requires_prior_auth", False)),
        )
        for r in rows
    ]
    return BenefitsResponse(planId=plan_id, benefits=benefits)
