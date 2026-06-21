# SPEC — 62 · WS-4 SBC RAG Schema

> **Commit**: `feat(ws4/rag): SBC RAG request/response Pydantic schemas`
> **File**: `services/eligibility/src/eligibility/schemas/sbc_rag.py`

---

## Purpose

Defines the typed contract between the API layer and callers (voice agent tools,
frontend, other services). No business logic — pure data shapes.

---

## Models

### `SBCRagRequest`

```python
class SBCRagRequest(BaseModel):
    planId: uuid.UUID          # which plan's chunks to search
    query:  str                # natural-language query, 1–1 000 chars
    topK:   int = Field(5, ge=1, le=20)  # chunks to return
```

`topK` is capped at 20 — the HNSW index is accurate at this range and returning
more chunks would bloat the voice agent's context window.

### `SBCChunkOut`

```python
class SBCChunkOut(BaseModel):
    chunkText:   str    # the raw benefit passage
    sectionName: str    # section label from SBCParserRunner / pdfplumber
    sourceFile:  str    # originating PDF filename
    distance:    float  # cosine distance — lower = more relevant
```

`distance` is exposed so callers can apply their own relevance threshold
(e.g. the hallucination guard discards chunks with `distance > 0.4`).

### `SBCRagResponse`

```python
class SBCRagResponse(BaseModel):
    planId: uuid.UUID
    query:  str
    chunks: list[SBCChunkOut]   # ordered by distance ascending
```

---

## Design Decisions

- **camelCase** — matches every other schema in this service.
- **No `score` field** — callers use raw cosine distance; a score (`1 - distance`)
  would require an extra convention (higher = better) that conflicts with how
  pgvector orders results.
- **`topK` max = 20** — beyond this the HNSW index recall degrades and latency
  grows; the voice agent uses `topK=5` by default.

---

## Acceptance Criteria

- `SBCRagRequest(planId=..., query="...", topK=5)` constructs without error.
- `topK=0` and `topK=21` raise `ValidationError`.
- `query=""` raises `ValidationError`.
