"""Cost estimation: copay / deductible / OOP math from member YTD state + benefits.

All money is integer cents. The estimate is intentionally conservative: with a copay
benefit the cost is the copay; with coinsurance before the deductible is met the member
pays the negotiated rate up to the remaining deductible (we surface that range).
"""

from __future__ import annotations

from typing import Any

from eligibility.lib.money import cents_to_usd
from eligibility.schemas.cost import CostEstimateResponse


def build_cost_estimate(
    result: dict[str, Any], cost_type: str, service: str | None
) -> CostEstimateResponse:
    member = result["member"]
    benefit = result.get("benefit")

    ded_total = result.get("plan_deductible_cents")
    oop_max = result.get("plan_oop_cents")
    ded_spent = member.get("deductible_ytd_cents") or 0
    oop_spent = member.get("oop_ytd_cents") or 0
    ded_remaining = max(0, (ded_total or 0) - ded_spent)
    oop_remaining = max(0, (oop_max or 0) - oop_spent)

    copay = benefit["copay_amount_cents"] if benefit else None
    coins = (
        float(benefit["coinsurance_percentage"])
        if benefit and benefit["coinsurance_percentage"] is not None
        else None
    )

    facts: list[str] = []
    fields: dict[str, Any] = {"memberId": member["member_id"], "costType": cost_type, "facts": facts}

    if cost_type == "deductible":
        fields.update(
            deductibleTotalCents=ded_total,
            deductibleSpentCents=ded_spent,
            deductibleRemainingCents=ded_remaining,
        )
        facts.append(f"deductible {cents_to_usd(ded_total)} total")
        facts.append(f"deductible {cents_to_usd(ded_spent)} met year-to-date")
        facts.append(f"deductible {cents_to_usd(ded_remaining)} remaining")
    elif cost_type == "oop":
        fields.update(
            oopMaxCents=oop_max,
            oopSpentCents=oop_spent,
            oopRemainingCents=oop_remaining,
        )
        facts.append(f"out-of-pocket max {cents_to_usd(oop_max)}")
        facts.append(f"out-of-pocket {cents_to_usd(oop_spent)} spent year-to-date")
        facts.append(f"out-of-pocket {cents_to_usd(oop_remaining)} remaining")
    else:  # "copay" or "service"
        label = service or "this service"
        if copay is not None:
            fields.update(copayAmountCents=copay, estimateLowCents=copay, estimateHighCents=copay)
            facts.append(f"{label} copay {cents_to_usd(copay)}")
        elif coins is not None:
            fields.update(
                coinsurancePercentage=coins,
                deductibleRemainingCents=ded_remaining,
                estimateLowCents=0,
                estimateHighCents=ded_remaining,
            )
            facts.append(f"{label} {coins:g}% coinsurance after deductible")
            facts.append(f"deductible {cents_to_usd(ded_remaining)} remaining")
        else:
            facts.append(f"no cost information found for '{label}'")

    return CostEstimateResponse(**fields)
