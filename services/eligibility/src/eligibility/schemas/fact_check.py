"""Request/response schemas for POST /api/v1/fact_check."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FactCheckRequest(BaseModel):
    answer: str
    facts: list[str] = Field(default_factory=list)
    ragFacts: list[str] = Field(default_factory=list)
    claimTypes: list[str] = Field(default_factory=lambda: ["amount", "tier", "boolean"])


class FactCheckResponse(BaseModel):
    grounded: bool
    guardReason: str
    ungroundedClaims: list[str]
    mode: str
