"""Response schemas for provider search and detail."""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    npi: str
    firstName: Optional[str]
    lastName: Optional[str]
    organizationName: Optional[str]
    credentialText: Optional[str]
    taxonomyCode: Optional[str]
    taxonomyDescription: Optional[str]
    addressLine1: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip: Optional[str]
    phone: Optional[str]
    acceptingNewPatients: Optional[bool]
    qualityRating: Optional[float]
    hospitalName: Optional[str]
    specialtyCodes: Optional[list[str]]


class ProviderSearchResponse(BaseModel):
    total: int
    providers: list[ProviderOut]


class ProviderNearItem(ProviderOut):
    distanceKm: float
    inNetwork: bool
    specialty: Optional[str] = None


class ProviderNearResponse(BaseModel):
    total: int
    query: dict
    providers: list[ProviderNearItem]
