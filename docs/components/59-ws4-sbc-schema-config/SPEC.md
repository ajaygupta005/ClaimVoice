# SPEC-2 — Schema & Config (sbc_chunks migration + eligibility settings)

> **Commit**: `feat(ws4): sbc_chunks migration, voyageai dependency, voyage_api_key config`

---

## Embedding Model

**Voyage AI `voyage-4-large`** — MoE architecture, current SOTA on RTEB as of Jan 2026.
Supports 2048/1024/512/256 dimensions via Matryoshka Representation Learning (MRL).
We use **1024 dims**. 200M tokens/month free on the voyage-4 series.

Do not change the dimension without re-embedding all chunks — the HNSW index is
dimension-specific.

---

## New Table: `sbc_chunks`

```sql
CREATE TABLE sbc_chunks (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id          UUID         NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    source_file      TEXT         NOT NULL,   -- e.g. "aetna_epo_basic_plan.pdf"
    section_name     TEXT         NOT NULL,   -- section label from SBCParserRunner
    chunk_index      SMALLINT     NOT NULL,   -- 0-based position within section
    chunk_text       TEXT         NOT NULL,
    embedding        vector(1024) NOT NULL,
    page_number      SMALLINT,
    audit_created_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (plan_id, source_file, section_name, chunk_index)
);

CREATE INDEX sbc_chunks_hnsw_idx
    ON sbc_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX sbc_chunks_plan_id_idx ON sbc_chunks (plan_id);
```

### HNSW vs IVFFlat

HNSW is chosen because:
- Better recall at low `ef_search` values (our `top_k` is 5)
- No training step — IVFFlat needs `VACUUM ANALYZE` after bulk inserts
- Corpus is small (~400 rows); HNSW memory overhead is negligible

See ADR-0005.

---

## Alembic Migration

**File:** `services/eligibility/alembic/versions/002_sbc_chunks.py`

- `down_revision = "001"` — chains after the base schema migration
- Enables the `vector` extension (deferred from 001 intentionally)
- Creates the table, HNSW index, and plan_id B-tree index in one `upgrade()`
- `downgrade()` drops the table (cascade drops the indexes)

Run:
```bash
cd services/eligibility
DATABASE_URL=postgresql://claimvoice:changeme@localhost:5432/claimvoice \
  uv run alembic upgrade head
```

Verify:
```sql
\d sbc_chunks
-- should show vector(1024) column and both indexes
```

---

## Config Changes

### `services/eligibility/src/eligibility/core/config.py`

```python
class Settings(BaseSettings):
    ...
    voyage_api_key: str = ""  # required for sbc_embed_ingest and sbc_rag
```

The key is read from `VOYAGE_API_KEY` in the environment / `.env` file via
pydantic-settings. Never hard-code it.

### `.env.example`

```
# Voyage AI — embeddings for SBC RAG (voyage-4-large, 200M tokens/month free)
VOYAGE_API_KEY=
```

Get a free key at https://dash.voyageai.com.

---

## Dependencies

Add to `services/eligibility/pyproject.toml` under `[project.dependencies]`:

```toml
"voyageai>=0.3.0",
```

The Voyage AI Python SDK. Already available on PyPI; no C extensions required.

---

## Acceptance Criteria

- `alembic upgrade head` runs clean (both 001 and 002).
- `\d sbc_chunks` shows `embedding vector(1024)` column, HNSW index, and plan_id index.
- `Settings().voyage_api_key` reads from `VOYAGE_API_KEY` env var.
