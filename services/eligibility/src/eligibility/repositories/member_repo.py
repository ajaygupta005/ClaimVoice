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
