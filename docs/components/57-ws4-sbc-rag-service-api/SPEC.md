# SPEC — 57 · WS-4 SBC RAG Service & API

> **Commit**: `feat(ws4/rag): Voyage AI query embedding, retrieve_chunks service, POST /sbc/retrieve endpoint`
> **Files**:
> - `services/eligibility/src/eligibility/services/sbc_rag.py`
> - `services/eligibility/src/eligibility/api/v1/sbc_rag.py`
> - `services/eligibility/src/eligibility/api/v1/__init__.py`

---

## Service: `retrieve_chunks`

```python
def retrieve_chunks(
    plan_id: uuid.UUID,
    query:   str,
    top_k:   int = 5,
) -> SBCRagResponse:
```

### Flow

```
query string
    │
    ▼
voyageai.Client.embed([query], model="voyage-4-large", input_type="query")
    │  1 024-dim vector
    ▼
search_sbc_chunks(session, plan_id, query_vec, top_k)   ← repo layer
    │  list[dict]
    ▼
SBCRagResponse(planId, query, chunks=[SBCChunkOut(...), ...])
```

### `input_type="query"` vs `"document"`

Voyage AI distinguishes embedding intent:
- `"document"` — used when ingesting chunks (Stage C, `sbc_embed_ingest.py`)
- `"query"` — used when embedding the search query (this service)

Using the correct type improves retrieval quality by ~5–10% on BEIR benchmarks.
Mixing them (query embedded as document) silently degrades recall.

### Why one Voyage call per request?

Each user turn produces exactly one query embedding (1 text × 1 024 dims ≈
~8 KB). The free-tier budget is not a concern here — the RAG endpoint is called
on demand, not in bulk. Batching would add latency with no benefit.

---

## API Router

### Endpoint

```
POST /api/v1/sbc/retrieve
Content-Type: application/json

{
    "planId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "query":  "Is physical therapy covered?",
    "topK":   5
}
```

### Response

```json
{
    "planId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "query":  "Is physical therapy covered?",
    "chunks": [
        {
            "chunkText":   "Physical therapy is covered at 80% after deductible...",
            "sectionName": "benefits",
            "sourceFile":  "aetna_epo_basic_plan.pdf",
            "distance":    0.147
        }
    ]
}
```

### Error cases

| Condition | Status | Detail |
|---|---|---|
| `VOYAGE_API_KEY` not set | 503 | `"VOYAGE_API_KEY is not configured"` |
| Plan has no chunks | 200 | `chunks: []` (not an error — caller decides) |
| Voyage API unavailable | 500 | propagated exception |

### Why POST not GET?

The query string can be up to 1 000 characters. URL-encoding a long query in a
`GET` parameter creates bookmarkability/logging issues and can exceed proxy URL
length limits (typically 2 048 chars). POST with a JSON body is conventional for
semantic search endpoints.

---

## Router Registration (`api/v1/__init__.py`)

```python
from .sbc_rag import router as sbc_rag_router
router.include_router(sbc_rag_router)
```

---

## How the Voice Agent Uses This

The `check_coverage` LangGraph tool calls this endpoint before composing its
answer:

```
User: "Is my MRI covered?"
  → tool: POST /api/v1/sbc/retrieve { planId, query: "MRI coverage", topK: 5 }
  → top chunks injected into Claude's context
  → Claude answers grounded in retrieved text
  → hallucination guard verifies the answer against the chunks
```

---

## Acceptance Criteria

- `POST /api/v1/sbc/retrieve` with valid planId + query returns `200` with
  at least 1 chunk (given seeded data).
- Returns `503` when `VOYAGE_API_KEY` is empty.
- Chunks are ordered by `distance` ascending (most relevant first).
- `topK=1` returns exactly 1 chunk.
- Voyageai call uses `input_type="query"` (not `"document"`).
