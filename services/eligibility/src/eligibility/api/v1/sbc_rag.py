"""POST /api/v1/sbc/retrieve — pgvector RAG over SBC benefit chunks."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from eligibility.lib.embeddings import EmbeddingProviderUnavailable
from eligibility.schemas.sbc_rag import SBCRagRequest, SBCRagResponse
from eligibility.services.sbc_rag import retrieve_chunks

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/sbc/retrieve", response_model=SBCRagResponse)
def sbc_retrieve(request: SBCRagRequest) -> SBCRagResponse:
    try:
        return retrieve_chunks(request.planId, request.query, request.topK)
    except EmbeddingProviderUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.warning(
            "sbc_rag.retrieve_failed",
            exc_info=exc,
            extra={"plan_id": request.planId, "top_k": request.topK},
        )
        raise HTTPException(
            status_code=502,
            detail="SBC RAG retrieval failed",
        ) from exc
