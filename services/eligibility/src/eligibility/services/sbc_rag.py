"""SBC RAG: embed a query and retrieve the closest chunks (Azure/Voyage embeddings)."""

from __future__ import annotations

import uuid

from eligibility.lib.db import db_session
from eligibility.lib.embeddings import embed_query
from eligibility.repositories.sbc_rag_repo import search_sbc_chunks
from eligibility.schemas.sbc_rag import SBCChunkOut, SBCRagResponse


def retrieve_chunks(plan_id: uuid.UUID, query: str, top_k: int = 5) -> SBCRagResponse:
    query_vec: list[float] = embed_query(query)

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
