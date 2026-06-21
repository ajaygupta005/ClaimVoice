# SPEC-4 — Tests & Validation

> **Commit**: `test(ws4): unit and integration tests for sbc_embed_ingest`

---

## Unit Tests (`services/eligibility/tests/unit/test_sbc_embed_ingest.py`)

All tests run without a database or Voyage API key.

| Test | Input | Assertion |
|---|---|---|
| `test_chunk_text_basic` | 800-word string, `chunk_size=400, overlap=50` | 2 chunks; last 50 words of chunk 0 == first 50 words of chunk 1 |
| `test_chunk_text_short` | 10-word string, `min_chunk_words=20` | Returns `[]` (below minimum) |
| `test_chunk_text_exact_window` | Exactly 400 words | 1 chunk, no second window |
| `test_chunk_text_empty` | `""` | Returns `[]` |

---

## Integration Tests (`services/eligibility/tests/integration/test_sbc_embed_ingest.py`)

Require a live PostgreSQL instance (`DATABASE_URL`) and a real Voyage API key
(`VOYAGE_API_KEY`). Skipped automatically when either is absent.

| Test | What it does |
|---|---|
| `test_bulk_insert_idempotent` | Insert same rows twice via `bulk_insert_chunks`; assert count stays the same |
| `test_ingest_pdf_inserts_rows` | Run `ingest_pdf` on a real PDF; assert `sbc_chunks` row count > 0 |
| `test_ingest_pdf_idempotent` | Run `ingest_pdf` twice; assert row count unchanged on second run |
| `test_pgvector_similarity_query` | Embed a query string; assert `embedding <=> vec < 0.5` for top result |

A fixed `plan_id` (`aaaaaaaa-0001-0001-0001-000000000001`) is seeded in a DB
fixture and cleaned up after each test.

---

## Standalone Smoke Test (`scripts/test_sbc_chunk_embed.py`)

One-shot script used during development to verify chunking and embedding without
running the full pipeline. Takes 4 NYC OLR SBC PDFs and:

1. Extracts text via pdfplumber
2. Chunks with `chunk_text(chunk_size=400, overlap=50)`
3. Embeds in batches of 3 (free-tier safe)
4. Prints per-plan chunk counts and estimated storage

Not part of the CI test suite — useful for manual validation.

---

## Rollback

```sql
-- Remove all embedded chunks for one plan (safe to re-embed after fixing the PDF)
DELETE FROM sbc_chunks WHERE plan_id = '<uuid>';

-- Full rollback: drop the table
-- cd services/eligibility && uv run alembic downgrade 001
```

---

## Full Acceptance Checklist

- [x] `alembic upgrade head` runs clean (001 + 002)
- [x] `python data/ingest/sbc_embed_ingest.py` completes on 4 NYC SBC PDFs
- [x] `SELECT COUNT(*) FROM sbc_chunks` = 32
- [x] `SELECT pg_size_pretty(pg_total_relation_size('sbc_chunks'))` = 776 kB
- [x] Re-run produces no new rows (idempotent)
- [x] `voyage_api_key` read from env — never hard-coded
- [x] `chunk_text()` unit tests pass
- [ ] `dvc repro` picks up `sbc_embed` stage from a clean state
- [ ] Re-run produces no new `audit_log` entries
