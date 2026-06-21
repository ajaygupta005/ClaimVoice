# SPEC — 56 · WS-4 SBC RAG Repository

> **Commit**: `feat(ws4/rag): pgvector cosine similarity search repository`
> **File**: `services/eligibility/src/eligibility/repositories/sbc_rag_repo.py`

---

## Purpose

Encapsulates the pgvector similarity query against `sbc_chunks`. No Voyage AI
dependency — accepts a pre-computed embedding vector and returns raw rows.
This separation means the query can be unit-tested with a fake vector without
needing a Voyage API key.

---

## Function

```python
def search_sbc_chunks(
    session: Session,
    plan_id: uuid.UUID,
    query_embedding: list[float],   # 1024-dim vector from Voyage AI
    top_k: int = 5,
) -> list[dict]:
```

### SQL

```sql
SELECT
    chunk_text,
    section_name,
    source_file,
    (embedding <=> :query_vec::vector) AS distance
FROM sbc_chunks
WHERE plan_id = :plan_id
ORDER BY embedding <=> :query_vec::vector
LIMIT :top_k
```

### Vector serialisation

pgvector expects the vector literal as a bracket-enclosed comma-separated
string: `[0.12, -0.34, ...]`. The function builds this with:

```python
vec_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"
```

This avoids any ORM type-mapping issues with psycopg3's binary protocol.

---

## Operator: `<=>` (cosine distance)

pgvector supports three distance operators:

| Operator | Metric | Use case |
|---|---|---|
| `<=>` | Cosine distance | Semantic similarity — **chosen** |
| `<->` | L2 (Euclidean) | Magnitude-sensitive |
| `<#>` | Negative inner product | Dot-product search |

Cosine distance is correct here because voyage-4-large embeddings are
unit-normalised — cosine distance and negative inner product are equivalent,
but `<=>` is more readable.

---

## Why `WHERE plan_id = :plan_id`?

The HNSW index is global across all plans. Without the plan filter, a query
about "deductible" could return chunks from a different member's plan.
The `plan_id` B-tree index (`sbc_chunks_plan_id_idx`) is applied first by
the planner, narrowing the candidate set before HNSW re-ranks.

---

## Return Shape

```python
[
    {
        "chunk_text":   str,
        "section_name": str,
        "source_file":  str,
        "distance":     float,   # 0.0 (identical) → 2.0 (opposite)
    },
    ...
]
```

---

## Acceptance Criteria

- Returns at most `top_k` rows, ordered by `distance` ascending.
- Returns `[]` when `plan_id` has no chunks in `sbc_chunks`.
- Does not raise when `query_embedding` is a zero vector (returns max-distance rows).
