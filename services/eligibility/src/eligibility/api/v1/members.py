"""GET /api/v1/members/{member_id}/summary"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from eligibility.lib.db import db_session
from eligibility.repositories.member_repo import get_member_with_plan
from eligibility.schemas.member import MemberOut, MemberSummaryResponse, PlanOut

router = APIRouter()


@router.get("/members/{member_id}/summary", response_model=MemberSummaryResponse)
def member_summary(member_id: str) -> MemberSummaryResponse:
    with db_session() as session:
        row = get_member_with_plan(session, member_id)

    if row is None:
        raise HTTPException(status_code=404, detail=f"Member '{member_id}' not found")

    name = " ".join(filter(None, [row.get("first_name"), row.get("last_name")])) or member_id

    member = MemberOut(
        memberId=row["member_id"],
        name=name,
        eligibilityStatus=row["eligibility_status"] or "unknown",
        deductibleYtdCents=row["deductible_ytd_cents"],
        oopYtdCents=row["oop_ytd_cents"],
    )
    plan = PlanOut(
        id=row["plan_id"],
        name=row["plan_marketing_name"],
        issuer=row.get("issuer_name"),
        year=row.get("plan_year"),
        type=row.get("plan_type"),
        metalLevel=row.get("metal_level"),
        hsaEligible=row.get("hsa_eligible"),
        state=row.get("service_area_state"),
    )
    return MemberSummaryResponse(member=member, plan=plan)
