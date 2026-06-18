"""Request/response schemas for POST /api/v1/cost/estimate."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class CostEstimateRequest(BaseModel):
    memberId: str
    costType: Literal["copay", "deductible", "oop", "service"] = "service"
    service: Optional[str] = None


class CostEstimateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    memberId: str
    costType: str
    copayAmountCents: Optional[int] = None
    coinsurancePercentage: Optional[float] = None
    deductibleTotalCents: Optional[int] = None
    deductibleSpentCents: Optional[int] = None
    deductibleRemainingCents: Optional[int] = None
    oopMaxCents: Optional[int] = None
    oopSpentCents: Optional[int] = None
    oopRemainingCents: Optional[int] = None
    estimateLowCents: Optional[int] = None
    estimateHighCents: Optional[int] = None
    facts: list[str]
