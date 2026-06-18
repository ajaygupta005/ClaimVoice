"""Response schema for GET /api/v1/coverage."""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CoverageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    memberId: str
    planId: uuid.UUID
    service: str
    matchedBenefit: Optional[str]
    covered: bool
    networkType: str
    copayAmountCents: Optional[int]
    coinsurancePercentage: Optional[float]
    requiresPriorAuth: bool
    deductibleRemainingCents: int
    oopRemainingCents: int
    # Human-readable claim strings the hallucination guard / fact_check can verify against.
    facts: list[str]
