"""SBC RAG client — calls POST /api/v1/sbc/retrieve on the eligibility service.

Used as a grounding fallback for coverage and formulary questions when structured
tool results are missing, ambiguous, or need supporting text evidence.

Structured tools remain the primary source of truth. This client is only called
when the tool result is an error, inconclusive, or explicitly needs citation support.

Failure modes return an explicit RagResult with a non-empty fallback_reason so
callers never infer "not covered" from an empty chunks list.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from voice_agent.lib.logger import logger


@dataclass
class SBCChunk:
    chunk_text: str
    section_name: str
    source_file: str
    distance: float


@dataclass
class RagResult:
    """Result from a single SBC RAG retrieval attempt."""

    attempted: bool = False
    available: bool = False
    chunks: list[SBCChunk] = field(default_factory=list)
    fallback_reason: str = ""   # non-empty when RAG is unavailable/failed/empty
    source: str = ""            # "eligibility-sbc-rag" when successful

    @property
    def chunks_count(self) -> int:
        return len(self.chunks)

    def to_dict(self) -> dict:
        return {
            "ragAttempted": self.attempted,
            "ragAvailable": self.available,
            "ragChunksCount": self.chunks_count,
            "ragFallbackReason": self.fallback_reason,
            "ragSource": self.source,
        }


_NOT_ATTEMPTED = RagResult(attempted=False, fallback_reason="rag_not_applicable")

# Intents that benefit from SBC RAG evidence.
_RAG_INTENTS = {"coverage", "formulary"}


def should_attempt_rag(intent: str, tool_ok: bool) -> bool:
    """Return True when RAG should be called for this intent.

    RAG is attempted when:
    - Intent is coverage or formulary (other intents don't use SBC text)
    - The structured tool call either failed or the intent is coverage
      (formulary uses RAG only as supporting evidence on tool failure)
    """
    if intent not in _RAG_INTENTS:
        return False
    # Always attempt for coverage; for formulary only on tool failure
    if intent == "coverage":
        return True
    return not tool_ok  # formulary: only when structured tool failed


def retrieve(
    plan_id: str,
    query: str,
    *,
    base_url: str,
    top_k: int = 3,
    timeout: float = 5.0,
) -> RagResult:
    """Call POST /api/v1/sbc/retrieve and return a RagResult.

    Never raises — all errors are captured in fallback_reason.
    """
    if not plan_id:
        return RagResult(
            attempted=True,
            available=False,
            fallback_reason="missing_plan_id",
        )

    url = f"{base_url}/api/v1/sbc/retrieve"
    payload = {"planId": plan_id, "query": query, "topK": top_k}

    try:
        r = httpx.post(url, json=payload, timeout=timeout)
    except httpx.TimeoutException:
        logger.warning("sbc_rag.timeout", url=url, query=query[:80])
        return RagResult(
            attempted=True,
            available=False,
            fallback_reason="rag_timeout",
        )
    except httpx.RequestError as exc:
        logger.warning("sbc_rag.request_error", url=url, error=str(exc))
        return RagResult(
            attempted=True,
            available=False,
            fallback_reason="rag_service_unavailable",
        )

    if r.status_code == 503:
        logger.info("sbc_rag.unavailable_503", url=url)
        return RagResult(
            attempted=True,
            available=False,
            fallback_reason="rag_key_missing",
        )

    if not r.is_success:
        logger.warning("sbc_rag.http_error", status=r.status_code, url=url)
        return RagResult(
            attempted=True,
            available=False,
            fallback_reason=f"rag_http_{r.status_code}",
        )

    try:
        data = r.json()
        chunks = [
            SBCChunk(
                chunk_text=c.get("chunkText", ""),
                section_name=c.get("sectionName", ""),
                source_file=c.get("sourceFile", ""),
                distance=float(c.get("distance", 1.0)),
            )
            for c in data.get("chunks", [])
        ]
    except Exception as exc:
        logger.warning("sbc_rag.parse_error", error=str(exc))
        return RagResult(
            attempted=True,
            available=False,
            fallback_reason="rag_parse_error",
        )

    if not chunks:
        return RagResult(
            attempted=True,
            available=True,
            chunks=[],
            fallback_reason="rag_empty_chunks",
            source="eligibility-sbc-rag",
        )

    return RagResult(
        attempted=True,
        available=True,
        chunks=chunks,
        fallback_reason="",
        source="eligibility-sbc-rag",
    )
