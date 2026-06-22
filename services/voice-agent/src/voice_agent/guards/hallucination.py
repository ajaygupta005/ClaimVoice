"""Hallucination guard client — verify an answer is grounded before TTS.

``mode="http"`` posts the answer + grounding facts to WS-4 ``POST /api/v1/fact_check``;
``mode="mock"`` (or any HTTP error) runs the same deterministic matcher in-process so the
graph stays offline in tests. The in-process matcher mirrors WS-4's mock fact_check
(dollar amounts, formulary tiers, coverage booleans).

Component 69: guard now accepts RAG chunks as additional grounding evidence and returns
structured metadata — guardReasonCode, supportedBy, unsupportedClaims, ragFactsUsed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import httpx

_AMOUNT = re.compile(r"\$[\d,]+(?:\.\d{2})?")
_TIER = re.compile(r"[Tt]ier\s+\d+")


@dataclass
class GuardResult:
    """Structured output from the hallucination guard (Component 69)."""
    grounded: bool
    reason: str
    reason_code: str = ""          # supported_by_structured_tool | supported_by_sbc_rag |
                                   #   unsupported_claim | no_facts_available | rag_unavailable
    supported_by: list[str] = field(default_factory=list)  # ["structured_tool"] | ["sbc_rag"] | both
    unsupported_claims: list[str] = field(default_factory=list)
    rag_facts_used: int = 0        # number of RAG chunks consumed as evidence


def _extract_rag_texts(rag_chunks: list[dict[str, Any]]) -> list[str]:
    """Pull chunk_text strings from the serialised chunk dicts stored in state."""
    return [c.get("chunk_text", "") for c in rag_chunks if c.get("chunk_text")]


def check_in_process(
    answer: str,
    facts: list[str],
    rag_chunks: list[dict[str, Any]] | None = None,
) -> GuardResult:
    """
    Deterministic in-process guard.

    Facts come from two sources:
    - ``facts``: structured tool result strings (primary)
    - ``rag_chunks``: SBC chunk dicts from Component 68 (supporting evidence)

    Returns a GuardResult with populated reason_code and supported_by.
    """
    rag_chunks = rag_chunks or []
    rag_texts = _extract_rag_texts(rag_chunks)

    # Build combined text corpora
    tool_text = " ".join(facts).lower()
    tool_norm = tool_text.replace(",", "")
    rag_text = " ".join(rag_texts).lower()
    rag_norm = rag_text.replace(",", "")
    combined_text = (tool_text + " " + rag_text).strip()

    has_tool_facts = bool(tool_text.strip())
    has_rag_facts = bool(rag_text.strip())

    if not has_tool_facts and not has_rag_facts:
        return GuardResult(
            grounded=False,
            reason="no facts available to verify answer",
            reason_code="no_facts_available",
            supported_by=[],
            unsupported_claims=[],
            rag_facts_used=0,
        )

    ungrounded: list[str] = []

    for amt in _AMOUNT.findall(answer):
        amt_norm = amt.replace(",", "").lower()
        if amt_norm not in tool_norm and amt_norm not in rag_norm:
            ungrounded.append(amt)

    for tier in _TIER.findall(answer):
        tier_l = tier.lower()
        if tier_l not in tool_text and tier_l not in rag_text:
            ungrounded.append(tier)

    al = answer.lower()
    if "not covered" in al and "not covered" not in combined_text and "covered" in combined_text:
        ungrounded.append("not covered")
    has_prior_auth_fact = (
        "prior auth" in combined_text or "prior authorization" in combined_text
    )
    if (
        "prior authorization required" in al or "prior auth required" in al
    ) and not has_prior_auth_fact:
        ungrounded.append("prior authorization required")

    if ungrounded:
        return GuardResult(
            grounded=False,
            reason=f"ungrounded claims: {ungrounded}",
            reason_code="unsupported_claim",
            supported_by=[],
            unsupported_claims=ungrounded,
            rag_facts_used=len(rag_texts) if has_rag_facts else 0,
        )

    # Determine which source(s) supported the answer
    supported_by: list[str] = []
    if has_tool_facts:
        supported_by.append("structured_tool")
    if has_rag_facts:
        supported_by.append("sbc_rag")

    if "sbc_rag" in supported_by and "structured_tool" not in supported_by:
        reason_code = "supported_by_sbc_rag"
    else:
        reason_code = "supported_by_structured_tool"

    return GuardResult(
        grounded=True,
        reason="all claims grounded in tool result",
        reason_code=reason_code,
        supported_by=supported_by,
        unsupported_claims=[],
        rag_facts_used=len(rag_texts) if has_rag_facts else 0,
    )


def fact_check(
    answer: str,
    facts: list[str],
    mode: str,
    base_url: str,
    rag_chunks: list[dict[str, Any]] | None = None,
) -> GuardResult:
    """Return a GuardResult. Falls back to in-process on any HTTP failure."""
    rag_chunks = rag_chunks or []

    if mode == "http":
        rag_texts = _extract_rag_texts(rag_chunks)
        try:
            r = httpx.post(
                f"{base_url}/api/v1/fact_check",
                json={"answer": answer, "facts": facts, "ragFacts": rag_texts},
                # The Claude judge (~5s warm, more on cold start) is the only check
                # that catches semantic mismatches (e.g. an in-network figure applied
                # to an out-of-network question). On timeout we fall back to the
                # in-process matcher, which can't see that — so allow real headroom
                # to keep the safety guard on the LLM path.
                timeout=12.0,
            )
            r.raise_for_status()
            d = r.json()
            grounded = bool(d.get("grounded"))
            reason = d.get("guardReason") or (
                "all claims grounded in tool result" if grounded else "ungrounded claims found"
            )
            # WS-4 may return structured fields; use them when present, fallback gracefully
            supported_by = d.get("supportedBy") or (["structured_tool"] if grounded else [])
            unsupported_claims = d.get("unsupportedClaims") or []
            rag_facts_used = int(d.get("ragFactsUsed", len(rag_texts) if rag_texts else 0))
            if grounded:
                reason_code = d.get("guardReasonCode") or (
                    "supported_by_sbc_rag"
                    if supported_by == ["sbc_rag"]
                    else "supported_by_structured_tool"
                )
            else:
                reason_code = d.get("guardReasonCode") or "unsupported_claim"
            return GuardResult(
                grounded=grounded,
                reason=reason,
                reason_code=reason_code,
                supported_by=supported_by,
                unsupported_claims=unsupported_claims,
                rag_facts_used=rag_facts_used,
            )
        except Exception:
            pass

    return check_in_process(answer, facts, rag_chunks)
