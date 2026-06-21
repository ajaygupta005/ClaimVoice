"""POST /api/v1/sbc/retrieve — pgvector RAG over SBC benefit chunks."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from eligibility.core.config import settings
from eligibility.schemas.sbc_rag import SBCRagRequest, SBCRagResponse
from eligibility.services.sbc_rag import retrieve_chunks

router = APIRouter()


@router.post("/sbc/retrieve", response_model=SBCRagResponse)
def sbc_retrieve(request: SBCRagRequest) -> SBCRagResponse:
    if not settings.voyage_api_key:
        raise HTTPException(
            status_code=503,
            detail="VOYAGE_API_KEY is not configured — cannot embed query",
        )
    return retrieve_chunks(request.planId, request.query, request.topK)
