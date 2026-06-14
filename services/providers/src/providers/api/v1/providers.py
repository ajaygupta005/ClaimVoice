"""GET /api/v1/providers/search  and  GET /api/v1/providers/{npi}"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from providers.lib.db import db_session
from providers.repositories.provider_repo import get_provider_by_npi, search_providers
from providers.schemas.provider import ProviderOut, ProviderSearchResponse

router = APIRouter()


def _row_to_provider(r: dict) -> ProviderOut:
    return ProviderOut(
        id=r["id"],
        npi=r["npi"],
        firstName=r.get("first_name"),
        lastName=r.get("last_name"),
        organizationName=r.get("organization_name"),
        credentialText=r.get("credential_text"),
        taxonomyCode=r.get("taxonomy_code"),
        taxonomyDescription=r.get("taxonomy_description"),
        addressLine1=r.get("practice_location_address_line_1"),
        city=r.get("practice_location_city"),
        state=r.get("practice_location_state"),
        zip=r.get("practice_location_zip"),
        phone=r.get("practice_location_phone"),
        acceptingNewPatients=r.get("accepting_new_patients"),
        qualityRating=float(r["quality_rating"]) if r.get("quality_rating") is not None else None,
        hospitalName=r.get("hospital_name"),
        specialtyCodes=r.get("specialty_codes"),
    )


@router.get("/providers/search", response_model=ProviderSearchResponse)
def provider_search(
    specialty: Optional[str] = Query(None, description="Specialty text (partial match)"),
    state: Optional[str] = Query(None, min_length=2, max_length=2, description="US state abbreviation"),
    zip: Optional[str] = Query(None, min_length=5, max_length=5, description="5-digit ZIP"),
    acceptingNewPatients: Optional[bool] = Query(None),
    planId: Optional[uuid.UUID] = Query(None, description="Plan UUID — accepted but in-network filtering not yet applied"),
    limit: int = Query(20, ge=1, le=100),
) -> ProviderSearchResponse:
    with db_session() as session:
        rows = search_providers(
            session,
            specialty=specialty,
            state=state,
            zip_code=zip,
            accepting_new_patients=acceptingNewPatients,
            limit=limit,
        )

    providers = [_row_to_provider(r) for r in rows]
    return ProviderSearchResponse(total=len(providers), providers=providers)


@router.get("/providers/{npi}", response_model=ProviderOut)
def provider_detail(npi: str) -> ProviderOut:
    with db_session() as session:
        row = get_provider_by_npi(session, npi)

    if row is None:
        raise HTTPException(status_code=404, detail=f"Provider NPI '{npi}' not found")

    return _row_to_provider(row)
