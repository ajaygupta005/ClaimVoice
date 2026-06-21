"""SBC RAG: embed a query with Voyage AI and retrieve the closest chunks."""

from __future__ import annotations

import uuid

import voyageai

from eligibility.core.config import settings
from eligibility.lib.db import db_session
from eligibility.repositories.sbc_rag_repo import search_sbc_chunks
from eligibility.schemas.sbc_rag import SBCChunkOut, SBCRagResponse


def retrieve_chunks(plan_id: uuid.UUID, query: str, top_k: int = 5) -> SBCRagResponse:
    client = voyageai.Client(api_key=settings.voyage_api_key)
    result = client.embed([query], model="voyage-4-large", input_type="query")
    query_vec: list[float] = result.embeddings[0]

    with db_session() as session:
        rows = search_sbc_chunks(session, plan_id, query_vec, top_k)

    return SBCRagResponse(
        planId=plan_id,
        query=query,
        chunks=[
            SBCChunkOut(
                chunkText=r["chunk_text"],
                sectionName=r["section_name"],
                sourceFile=r["source_file"],
                distance=float(r["distance"]),
            )
            for r in rows
        ],
    )
