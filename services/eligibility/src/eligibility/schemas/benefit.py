"""Response schemas for plan benefits."""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BenefitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    benefitName: Optional[str]
    serviceCategory: Optional[str]
    networkType: Optional[str]
    individualDeductibleCents: Optional[int]
    familyDeductibleCents: Optional[int]
    copayAmountCents: Optional[int]
    coinsurancePercentage: Optional[float]
    outOfPocketMaxCents: Optional[int]
    requiresPriorAuth: bool


class BenefitsResponse(BaseModel):
    planId: uuid.UUID
    benefits: list[BenefitOut]
