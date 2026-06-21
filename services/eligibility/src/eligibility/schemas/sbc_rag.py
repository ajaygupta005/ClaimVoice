"""Pydantic schemas for the SBC RAG retrieve endpoint."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class SBCRagRequest(BaseModel):
    planId: uuid.UUID
    query: str = Field(..., min_length=1, max_length=1000)
    topK: int = Field(default=5, ge=1, le=20)


class SBCChunkOut(BaseModel):
    chunkText: str
    sectionName: str
    sourceFile: str
    distance: float  # cosine distance — lower means more similar


class SBCRagResponse(BaseModel):
    planId: uuid.UUID
    query: str
    chunks: list[SBCChunkOut]
