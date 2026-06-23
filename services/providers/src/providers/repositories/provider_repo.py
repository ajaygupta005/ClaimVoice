"""Read-only repository helpers for provider search and detail."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

_SELECT_COLS = """
    id,
    npi,
    first_name,
    last_name,
    organization_name,
    credential_text,
    taxonomy_code,
    taxonomy_description,
    practice_location_address_line_1,
    practice_location_city,
    practice_location_state,
    practice_location_zip,
    practice_location_phone,
    accepting_new_patients,
    quality_rating,
    hospital_name,
    specialty_codes
"""


def _normalize_specialty(value: str) -> str:
    text = value.strip().lower()
    if "cardio" in text:
        return "cardio"
    if text in {"pcp", "primary care", "family practice"}:
        return "primary care"
    return value.strip()


def search_providers(
    session: Session,
    specialty: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
    accepting_new_patients: Optional[bool] = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Search providers by specialty text, state, or zip.  Results are sorted by:
      1. quality_rating DESC (NULLs last)
      2. accepting_new_patients DESC (True first)
      3. last_name / organization_name ASC

    planId is accepted at the API layer but in-network filtering is not yet applied.
    """
    clauses = []
    params: dict[str, Any] = {"limit": limit}

    if specialty:
        specialty = _normalize_specialty(specialty)
        clauses.append(
            "(taxonomy_description ILIKE :specialty OR "
            " EXISTS (SELECT 1 FROM unnest(specialty_codes) sc WHERE sc ILIKE :specialty))"
        )
        params["specialty"] = f"%{specialty}%"

    if state:
        clauses.append("practice_location_state = :state")
        params["state"] = state.upper()

    if zip_code:
        clauses.append("practice_location_zip = :zip_code")
        params["zip_code"] = zip_code[:5]

    if accepting_new_patients is not None:
        clauses.append("accepting_new_patients = :anp")
        params["anp"] = accepting_new_patients

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    rows = session.execute(
        text(f"""
            SELECT {_SELECT_COLS}
            FROM providers
            {where}
            ORDER BY
                quality_rating DESC NULLS LAST,
                accepting_new_patients DESC NULLS LAST,
                COALESCE(last_name, organization_name) ASC
            LIMIT :limit
        """),
        params,
    ).mappings().all()
    return [dict(r) for r in rows]


def get_provider_by_npi(session: Session, npi: str) -> Optional[dict[str, Any]]:
    """Return a single provider row by NPI, or None."""
    row = session.execute(
        text(f"SELECT {_SELECT_COLS} FROM providers WHERE npi = :npi"),
        {"npi": npi},
    ).mappings().first()
    return dict(row) if row else None


def near_candidates(session: Session, plan_id: Optional[Any] = None) -> list[dict[str, Any]]:
    """Candidate providers (with location WKT + in-network flag) for app-side geo ranking.

    ``in_network`` is true iff the provider is in-network for ``plan_id``; with no
    plan_id the flag is always false (in-network requires a plan). Geo distance and
    specialty/radius filtering happen in services/geo_search (no PostGIS on dev DB).
    """
    rows = session.execute(
        text(f"""
            SELECT {_SELECT_COLS}, ST_AsText(location::geometry) AS location,
                   EXISTS(
                       SELECT 1 FROM in_network i
                       WHERE i.provider_npi = providers.npi
                         AND i.plan_id = CAST(:pid AS uuid)
                   ) AS in_network
            FROM providers
            WHERE location IS NOT NULL
        """),
        {"pid": str(plan_id) if plan_id else None},
    ).mappings().all()
    return [dict(r) for r in rows]


def get_providers_by_npis(session: Session, npis: list[str]) -> list[dict[str, Any]]:
    """Return provider rows for a list of NPIs (missing NPIs are simply absent)."""
    if not npis:
        return []
    rows = session.execute(
        text(f"SELECT {_SELECT_COLS} FROM providers WHERE npi = ANY(:npis)"),
        {"npis": npis},
    ).mappings().all()
    return [dict(r) for r in rows]
