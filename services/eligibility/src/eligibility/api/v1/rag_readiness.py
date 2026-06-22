"""GET /api/v1/rag/readiness — SBC RAG readiness check (Component 71).

Returns HTTP 200 always; the payload conveys whether RAG is actually usable.
This endpoint is called by the voice-agent runtime/status and by scripts/start.py.

Checks performed:
  1. VOYAGE_API_KEY is configured.
  2. pgvector extension is available in Postgres.
  3. sbc_chunks table exists.
  4. sbc_chunks has at least one row.
  5. At least one chunk is linked to an existing plan.

No secret values are returned — only counts and status strings.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from eligibility.core.config import settings
from eligibility.lib.db import db_session

router = APIRouter()

RagStatusKind = Literal["ready", "key_missing", "table_missing", "empty", "no_plan_links", "db_error"]


class RagReadinessResponse(BaseModel):
    ragStatus: RagStatusKind
    ragReason: str
    sbcChunksCount: int = 0
    voyageConfigured: bool = False
    pgvectorAvailable: bool = False


def _check_rag_readiness() -> RagReadinessResponse:
    voyage_ok = bool(settings.voyage_api_key.strip())

    if not voyage_ok:
        return RagReadinessResponse(
            ragStatus="key_missing",
            ragReason="VOYAGE_API_KEY is not configured",
            voyageConfigured=False,
            pgvectorAvailable=False,
        )

    try:
        with db_session() as session:
            # 1. pgvector available?
            pgv_row = session.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            ).fetchone()
            pgvector_ok = pgv_row is not None

            if not pgvector_ok:
                return RagReadinessResponse(
                    ragStatus="table_missing",
                    ragReason="pgvector extension not installed",
                    voyageConfigured=True,
                    pgvectorAvailable=False,
                )

            # 2. sbc_chunks table exists?
            table_row = session.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'sbc_chunks'"
                )
            ).fetchone()

            if table_row is None:
                return RagReadinessResponse(
                    ragStatus="table_missing",
                    ragReason="sbc_chunks table does not exist — run migrations",
                    voyageConfigured=True,
                    pgvectorAvailable=True,
                )

            # 3. Row count
            count_row = session.execute(
                text("SELECT COUNT(*) FROM sbc_chunks")
            ).fetchone()
            total = int(count_row[0]) if count_row else 0

            if total == 0:
                return RagReadinessResponse(
                    ragStatus="empty",
                    ragReason="sbc_chunks table exists but contains no rows — run sbc_embed_ingest",
                    voyageConfigured=True,
                    pgvectorAvailable=True,
                    sbcChunksCount=0,
                )

            # 4. Plan-linked chunk count
            linked_row = session.execute(
                text(
                    "SELECT COUNT(*) FROM sbc_chunks sc "
                    "JOIN plans p ON sc.plan_id = p.id"
                )
            ).fetchone()
            linked = int(linked_row[0]) if linked_row else 0

            if linked == 0:
                return RagReadinessResponse(
                    ragStatus="no_plan_links",
                    ragReason=f"{total} chunks exist but none are linked to a known plan",
                    voyageConfigured=True,
                    pgvectorAvailable=True,
                    sbcChunksCount=total,
                )

            return RagReadinessResponse(
                ragStatus="ready",
                ragReason=f"{linked} plan-linked chunks available",
                voyageConfigured=True,
                pgvectorAvailable=True,
                sbcChunksCount=total,
            )

    except Exception as exc:
        return RagReadinessResponse(
            ragStatus="db_error",
            ragReason=f"database error: {type(exc).__name__}",
            voyageConfigured=voyage_ok,
            pgvectorAvailable=False,
        )


@router.get("/rag/readiness", response_model=RagReadinessResponse)
def rag_readiness() -> RagReadinessResponse:
    return _check_rag_readiness()
