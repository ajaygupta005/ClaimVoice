"""POST /api/v1/fact_check — verify an answer is grounded in supplied facts."""

from __future__ import annotations

from fastapi import APIRouter

from eligibility.core.config import settings
from eligibility.schemas.fact_check import FactCheckRequest, FactCheckResponse
from eligibility.services.fact_check import fact_check

router = APIRouter()


@router.post("/fact_check", response_model=FactCheckResponse)
def fact_check_endpoint(req: FactCheckRequest) -> FactCheckResponse:
    facts = [*req.facts, *req.ragFacts]
    return fact_check(
        req.answer,
        facts,
        req.claimTypes,
        mode=settings.fact_check_mode,
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model,
    )
