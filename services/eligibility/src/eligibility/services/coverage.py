"""Coverage logic: turn a member's matched benefit + deductible state into a
structured CoverageResponse plus human-readable facts for grounding."""

from __future__ import annotations

from typing import Any

from loguru import logger

from eligibility.core.config import settings
from eligibility.lib.money import cents_to_usd
from eligibility.schemas.coverage import CoverageResponse


def sbc_facts_for(plan_id: Any, service: str) -> list[str]:
    """Retrieve SBC passages for the plan as extra grounding facts.

    Called from the /coverage endpoint (not from the pure builder) so unit tests
    of build_coverage_response stay offline. Best-effort: returns [] when
    disabled, no embedding key, no chunks, or any error.
    """
    if not settings.sbc_rag_in_coverage:
        return []
    has_key = bool(
        (settings.sbc_embed_provider == "azure" and settings.azure_openai_api_key)
        or settings.voyage_api_key
    )
    if not has_key:
        return []
    try:
        from eligibility.services.sbc_rag import retrieve_chunks

        resp = retrieve_chunks(plan_id, service, top_k=settings.sbc_rag_top_k)
        facts: list[str] = []
        for chunk in resp.chunks:
            text = " ".join(chunk.chunkText.split())[:400]
            facts.append(
                f"From the plan's Summary of Benefits ({chunk.sectionName}): {text}"
            )
        return facts
    except Exception as exc:  # noqa: BLE001 — enrichment must never break coverage
        logger.warning("SBC RAG enrichment skipped: {}", exc)
        return []


def build_coverage_response(
    result: dict[str, Any], service: str, network_type: str
) -> CoverageResponse:
    """Build the response from a repository result.

    ``result`` shape: {member, benefit|None, plan_deductible_cents, plan_oop_cents}.
    """
    member = result["member"]
    benefit = result["benefit"]
    plan_ded = result.get("plan_deductible_cents") or 0
    plan_oop = result.get("plan_oop_cents") or 0

    ded_remaining = max(0, plan_ded - (member.get("deductible_ytd_cents") or 0))
    oop_remaining = max(0, plan_oop - (member.get("oop_ytd_cents") or 0))

    covered = benefit is not None
    matched = benefit["benefit_name"] if benefit else None
    copay = benefit["copay_amount_cents"] if benefit else None
    coins = (
        float(benefit["coinsurance_percentage"])
        if benefit and benefit["coinsurance_percentage"] is not None
        else None
    )
    pa = bool(benefit["requires_prior_auth"]) if benefit else False

    facts: list[str] = []
    if covered:
        facts.append(f"{matched or service} is covered ({network_type})")
        if copay is not None:
            facts.append(f"copay {cents_to_usd(copay)}")
        if coins is not None:
            facts.append(f"{coins:g}% coinsurance")
        if pa:
            facts.append("prior authorization required")
    else:
        facts.append(f"no {network_type} benefit found for '{service}'")
    facts.append(f"deductible {cents_to_usd(ded_remaining)} remaining")
    facts.append(f"out-of-pocket {cents_to_usd(oop_remaining)} remaining")

    return CoverageResponse(
        memberId=member["member_id"],
        planId=member["plan_id"],
        service=service,
        matchedBenefit=matched,
        covered=covered,
        networkType=network_type,
        copayAmountCents=copay,
        coinsurancePercentage=coins,
        requiresPriorAuth=pa,
        deductibleRemainingCents=ded_remaining,
        oopRemainingCents=oop_remaining,
        facts=facts,
    )
