"""pgvector similarity search against sbc_chunks."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session


def search_sbc_chunks(
    session: Session,
    plan_id: uuid.UUID,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    """Return the top-k chunks closest to query_embedding for the given plan."""
    vec_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"
    rows = session.execute(
        text("""
            SELECT
                chunk_text,
                section_name,
                source_file,
                (embedding <=> CAST(:query_vec AS vector)) AS distance
            FROM sbc_chunks
            WHERE plan_id = :plan_id
            ORDER BY embedding <=> CAST(:query_vec AS vector)
            LIMIT :top_k
        """),
        {"plan_id": str(plan_id), "query_vec": vec_literal, "top_k": top_k},
    ).mappings().all()
    return [dict(r) for r in rows]
