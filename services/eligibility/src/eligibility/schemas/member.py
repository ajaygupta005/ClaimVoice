"""Response schemas for member/plan data."""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    memberId: str
    name: str
    eligibilityStatus: str
    deductibleYtdCents: int
    oopYtdCents: int


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    issuer: Optional[str]
    year: Optional[int]
    type: Optional[str]
    metalLevel: Optional[str]
    hsaEligible: Optional[bool]
    state: Optional[str]


class MemberSummaryResponse(BaseModel):
    member: MemberOut
    plan: PlanOut
