"""Read-only repository helpers for members, plans, benefits, and formulary."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_member_with_plan(session: Session, member_id: str) -> Optional[dict[str, Any]]:
    """Return a dict with member + plan rows, or None if not found."""
    row = session.execute(
        text("""
            SELECT
                m.member_id,
                m.first_name,
                m.last_name,
                m.eligibility_status,
                m.deductible_ytd_cents,
                m.oop_ytd_cents,
                p.id          AS plan_id,
                p.plan_marketing_name,
                p.issuer_name,
                p.plan_year,
                p.plan_type,
                p.metal_level,
                p.hsa_eligible,
                p.service_area_state
            FROM members m
            JOIN plans p ON p.id = m.plan_id
            WHERE m.member_id = :member_id
        """),
        {"member_id": member_id},
    ).mappings().first()
    return dict(row) if row else None


def get_plan_benefits(session: Session, plan_id: uuid.UUID) -> list[dict[str, Any]]:
    """Return all benefit rows for a plan."""
    rows = session.execute(
        text("""
            SELECT
                id,
                benefit_name,
                service_category,
                network_type,
                individual_deductible_cents,
                family_deductible_cents,
                copay_amount_cents,
                coinsurance_percentage,
                out_of_pocket_max_cents,
                requires_prior_auth
            FROM plan_benefits
            WHERE plan_id = :plan_id
            ORDER BY service_category, benefit_name
        """),
        {"plan_id": str(plan_id)},
    ).mappings().all()
    return [dict(r) for r in rows]


def get_coverage(
    session: Session,
    member_id: str,
    service: str,
    network_type: str = "In Network",
) -> Optional[dict[str, Any]]:
    """Resolve a member's coverage for a service.

    Returns {member, benefit|None, plan_deductible_cents, plan_oop_cents} or None if
    the member does not exist. ``benefit`` is the best benefit row whose name or
    service_category matches ``service`` (name match preferred), within ``network_type``.
    """
    member = session.execute(
        text("""
            SELECT member_id, plan_id, eligibility_status, deductible_ytd_cents, oop_ytd_cents
            FROM members WHERE member_id = :mid
        """),
        {"mid": member_id},
    ).mappings().first()
    if member is None:
        return None

    pid = str(member["plan_id"])
    pattern = f"%{service}%"
    benefit = session.execute(
        text("""
            SELECT benefit_name, service_category, network_type, copay_amount_cents,
                   coinsurance_percentage, individual_deductible_cents,
                   out_of_pocket_max_cents, requires_prior_auth
            FROM plan_benefits
            WHERE plan_id = :pid AND network_type = :net
              AND (benefit_name ILIKE :pat OR service_category ILIKE :pat)
            ORDER BY (CASE WHEN benefit_name ILIKE :pat THEN 0 ELSE 1 END), benefit_name
            LIMIT 1
        """),
        {"pid": pid, "net": network_type, "pat": pattern},
    ).mappings().first()

    levels = session.execute(
        text("""
            SELECT MAX(individual_deductible_cents) AS ded,
                   MAX(out_of_pocket_max_cents) AS oop
            FROM plan_benefits WHERE plan_id = :pid AND network_type = :net
        """),
        {"pid": pid, "net": network_type},
    ).mappings().first()

    return {
        "member": dict(member),
        "benefit": dict(benefit) if benefit else None,
        "plan_deductible_cents": levels["ded"] if levels else None,
        "plan_oop_cents": levels["oop"] if levels else None,
    }


def search_formulary(
    session: Session,
    plan_id: uuid.UUID,
    query: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Case-insensitive substring search on drug_name within a plan."""
    rows = session.execute(
        text("""
            SELECT
                id,
                drug_name,
                ndc_code,
                formulary_tier,
                prior_auth_required,
                step_therapy_required,
                quantity_limit
            FROM formulary_drug
            WHERE plan_id = :plan_id
              AND drug_name ILIKE :pattern
            ORDER BY formulary_tier NULLS LAST, drug_name
            LIMIT :limit
        """),
        {"plan_id": str(plan_id), "pattern": f"%{query}%", "limit": limit},
    ).mappings().all()
    return [dict(r) for r in rows]
