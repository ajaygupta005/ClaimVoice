"""Response schemas for formulary drug lookup."""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FormularyDrugOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    drugName: str
    ndcCode: Optional[str]
    formularyTier: Optional[int]
    priorAuthRequired: bool
    stepTherapyRequired: bool
    quantityLimit: Optional[str]


class FormularySearchResponse(BaseModel):
    planId: uuid.UUID
    query: str
    drugs: list[FormularyDrugOut]


class FormularyLookupResponse(BaseModel):
    memberId: str
    planId: uuid.UUID
    query: str
    match: Optional[FormularyDrugOut]
    alternatives: list[FormularyDrugOut]
    onFormulary: bool
    # Human-readable claim strings for grounding.
    facts: list[str]
