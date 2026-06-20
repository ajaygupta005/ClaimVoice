"""Formulary lookup logic: best match + cheaper/equal-tier alternatives + facts."""

from __future__ import annotations

from typing import Any

from eligibility.schemas.formulary import FormularyDrugOut, FormularyLookupResponse


def drug_out(row: dict[str, Any]) -> FormularyDrugOut:
    """Map a snake_case formulary_drug row to the camelCase output schema."""
    return FormularyDrugOut(
        id=row["id"],
        drugName=row["drug_name"],
        ndcCode=row.get("ndc_code"),
        formularyTier=row.get("formulary_tier"),
        priorAuthRequired=bool(row.get("prior_auth_required", False)),
        stepTherapyRequired=bool(row.get("step_therapy_required", False)),
        quantityLimit=row.get("quantity_limit"),
    )


def build_formulary_lookup(
    member_id: str, result: dict[str, Any], query: str
) -> FormularyLookupResponse:
    match = result["match"]
    alternatives = result.get("alternatives") or []
    on_formulary = match is not None

    facts: list[str] = []
    if on_formulary:
        tier = match.get("formulary_tier")
        tier_str = f"Tier {tier}" if tier is not None else "covered"
        facts.append(f"{match['drug_name']} is on formulary, {tier_str}")
        if match.get("prior_auth_required"):
            facts.append("prior authorization required")
        if match.get("step_therapy_required"):
            facts.append("step therapy required")
    else:
        facts.append(f"{query} is not on the plan formulary")

    return FormularyLookupResponse(
        memberId=member_id,
        planId=result["plan_id"],
        query=query,
        match=drug_out(match) if match else None,
        alternatives=[drug_out(a) for a in alternatives],
        onFormulary=on_formulary,
        facts=facts,
    )
