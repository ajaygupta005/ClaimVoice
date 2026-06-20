"""GET /api/v1/providers/near — geo + specialty + in-network ranked provider search.

Reproduces the pinned eval semantics (eval/tasks/provider_lookup_eval.rank_providers):
specialty substring, Haversine distance within radius, in-network / accepting-new
filters, sorted by distance then quality.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from providers.core.config import settings
from providers.lib.db import db_session
from providers.repositories.provider_repo import near_candidates
from providers.schemas.provider import ProviderNearItem, ProviderNearResponse
from providers.services.geo_search import rank_near

router = APIRouter()


def _to_near_item(r: dict, distance_km: float) -> ProviderNearItem:
    return ProviderNearItem(
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
        distanceKm=distance_km,
        inNetwork=bool(r.get("in_network")),
        specialty=r.get("taxonomy_description"),
    )


@router.get("/providers/near", response_model=ProviderNearResponse)
def providers_near(
    specialty: str = Query(..., min_length=1),
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radiusKm: float = Query(None, gt=0, le=500),
    inNetworkOnly: bool = Query(False),
    acceptingNewOnly: bool = Query(False),
    planId: Optional[uuid.UUID] = Query(None),
    limit: int = Query(None, ge=1, le=100),
) -> ProviderNearResponse:
    radius = radiusKm if radiusKm is not None else settings.default_radius_km
    top_n = limit if limit is not None else settings.near_max_limit

    if inNetworkOnly and planId is None:
        raise HTTPException(status_code=400, detail="planId is required when inNetworkOnly is true")

    with db_session() as session:
        candidates = near_candidates(session, planId)

    query = {
        "specialty": specialty,
        "lat": lat,
        "lng": lng,
        "radius_km": radius,
        "in_network_only": inNetworkOnly,
        "accepting_new_only": acceptingNewOnly,
    }
    ranked = rank_near(query, candidates)[:top_n]
    items = [_to_near_item(row, dist) for row, dist in ranked]

    return ProviderNearResponse(
        total=len(items),
        query={
            "specialty": specialty,
            "lat": lat,
            "lng": lng,
            "radiusKm": radius,
            "inNetworkOnly": inNetworkOnly,
            "acceptingNewOnly": acceptingNewOnly,
            "planId": str(planId) if planId else None,
        },
        providers=items,
    )
