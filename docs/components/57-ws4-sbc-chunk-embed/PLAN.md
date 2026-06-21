# Component 40 — WS-4 SBC Chunk & Embed — Implementation Plan

> Step-by-step. Check off as you go. All work on branch `ws4-sbc-chunk-embed`.

---

## Phase 1 — Schema & Config

1. [x] Write `services/eligibility/alembic/versions/002_sbc_chunks.py` — creates `sbc_chunks`
       table with `vector(1024)` column, HNSW index (`m=16, ef_construction=64`), and
       `plan_id` B-tree index. Chain `down_revision = "001"`.

2. [x] Run `uv run alembic upgrade head` from `services/eligibility/` and confirm
       `\d sbc_chunks` shows the `vector` column and both indexes.

3. [x] Add `voyage_api_key: str = ""` to `Settings` in
       `services/eligibility/src/eligibility/core/config.py`.

4. [x] Add `VOYAGE_API_KEY=your_voyage_api_key_here` to `.env.example`.

5. [x] Add `voyageai>=0.3.0` to `[project.dependencies]` in
       `services/eligibility/pyproject.toml` and run `uv sync`.

---

## Phase 2 — Hydra Config

6. [x] Create `data/ingest/configs/sbc_embed_ingest.yaml` with keys:
       `sbc_dir`, `chunk_size` (400), `overlap` (50), `voyage_model` ("voyage-4-large"),
       `voyage_batch_size` (3 — free-tier safe), `voyage_sleep_s` (22.0), `min_chunk_words` (20),
       `database_url` (via `${oc.env:DATABASE_URL,...}`),
       `voyage_api_key` (via `${oc.env:VOYAGE_API_KEY,""}`).

---

## Phase 3 — Ingest Script

7. [x] Create `data/ingest/sbc_embed_ingest.py` with:
       - `chunk_text(text, chunk_size, overlap) -> list[str]` — word-window splitter
       - `embed_batch(client, texts) -> list[list[float]]` — Voyage AI call with
         `model="voyage-4-large"`, `input_type="document"`
       - `resolve_plan_id(conn, plan_name) -> uuid | None` — case-insensitive lookup
         against `plans.plan_marketing_name`; warns and skips if no match
       - `ingest_pdf(conn, client, cfg, pdf_path, plan_name, last_embed_time)` — orchestrates
         parse → chunk → embed → bulk insert → audit log; rate-limit sleep enforced
         cross-PDF via `last_embed_time` dict; retries up to 3× on 429
       - pdfplumber fallback when `document_ai` package not installed
       - `main()` — Hydra entrypoint; discovers `*.pdf` files in `sbc_dir`

8. [x] Verify inserts use `ON CONFLICT (plan_id, source_file, section_name, chunk_index)
       DO NOTHING` — never upsert, never truncate.

9. [x] Verify every processed PDF writes one row to `audit_log`
       (`table_name="sbc_chunks"`, `source="sbc_embed_ingest"`, `data_hash=SHA256`
       of the PDF bytes).

10. [x] Verify sections with fewer than `min_chunk_words` words are skipped with a
        `logger.debug` message — not silently dropped.

---

## Phase 4 — DVC Wiring

11. [x] Add `sbc_embed` stage to `dvc.yaml` after `sbc_download`:
        - `cmd`: `python data/ingest/sbc_embed_ingest.py`
        - `deps`: script file + config YAML + `data/raw/sbcs/`
        - `params`: `chunk_size`, `overlap`, `voyage_model` from config YAML
        - No `outs` (output is a DB table, not a file)

---

## Phase 5 — Tests

12. [x] Create `tests/unit/test_sbc_embed_ingest.py` with:
        - `test_chunk_text_basic` — 800-word input, `chunk_size=400, overlap=50`
          → assert 2 chunks, assert overlap words appear in both
        - `test_chunk_text_short` — input < `min_chunk_words` → assert `[]`
        - `test_chunk_text_exact_window` — input == `chunk_size` → assert 1 chunk
        - `test_chunk_text_empty` — empty string → assert `[]`

13. [x] Create `tests/integration/test_sbc_embed_ingest.py` (requires DB + Voyage key):
        - Seed one plan row with a fixed UUID
        - Run `ingest_pdf` against a test PDF (skip if file absent with `pytest.mark.skipif`)
        - Assert `sbc_chunks` rows exist for that `plan_id`
        - Re-run → assert row count unchanged (idempotent)
        - Run pgvector sanity query: embed "Is physical therapy covered?" and assert
          top-1 result has `embedding <=> query_vec < 0.5`

---

## Phase 6 — Smoke Test

14. [x] Run `python data/ingest/sbc_embed_ingest.py` end-to-end against the dev stack.
        Result: 4 NYC OLR SBC PDFs → 32 chunks → 776 KB in pgvector (64 KB heap + 392 KB HNSW index).

15. [x] Run the manual pgvector sanity query from SPEC acceptance criteria in psql:
        `SELECT pg_size_pretty(pg_total_relation_size('sbc_chunks')), COUNT(*) FROM sbc_chunks;`
        → 776 kB / 32 rows.

16. [ ] Run `dvc repro` from a clean state and confirm `sbc_embed` stage executes.

17. [ ] Confirm re-run produces no new `audit_log` entries (idempotency check).

---

## Infrastructure Changes

- `infra/postgres/Dockerfile` — extends `postgis/postgis:16-3.4` with `postgresql-16-pgvector`
  (base image lacks pgvector; required for `vector` extension)
- `docker-compose.yml` — postgres service changed from `image:` to `build: ./infra/postgres`
- `services/eligibility/alembic.ini` — created (was missing); `script_location = alembic`
- `services/eligibility/alembic/versions/001_init_schema.py` — added `from geoalchemy2 import
  Geography`; fixed extension name (`vector` not `pgvector`); `spatial_index=False` to avoid
  duplicate GiST index on stash-pop (superseded by rebase — now uses main's raw SQL approach)
- `data/ingest/configs/sbc_manifest.yaml` — updated with working NYC OLR government PDF URLs
  (original insurer CDN URLs returned 404)

---

## Commit message

```
feat(ws4): sbc chunk-and-embed pipeline with voyage-4-large and pgvector HNSW
```
