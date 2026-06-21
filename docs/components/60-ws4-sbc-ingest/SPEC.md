# SPEC-3 — Ingest Pipeline (sbc_embed_ingest + Hydra config + DVC)

> **Commit**: `feat(ws4): sbc_embed_ingest pipeline with Hydra config, NYC manifest, DVC wiring`

---

## Goal

Connect the SBC PDFs already downloaded to `data/raw/sbcs/` to the pgvector store so
the eligibility service can retrieve plan benefit passages at query time (Stage D,
`sbc_rag.py`).

**Out of scope:** the RAG query path (`sbc_rag.py`), the hallucination guard
(`fact_check.py`), and any changes to `services/document-ai/`.

---

## What Stage B Produces

`SBCParserRunner.__call__(pdf_path, document_id)` returns:

```python
{
  "document_id": str,
  "sections": [
    { "section_name": str, "raw_text": str, "benefit_rows": [...] },
    ...
  ]
}
```

Section labels: `plan_summary`, `benefits`, `coverage_exclusions`,
`cost_sharing`, `coverage_period`, `network_info`.

When `document_ai` is not installed (e.g. during local dev without the ML stack),
the script falls back to **pdfplumber** to extract raw text and treats the whole
document as a single `full_document` section.

---

## What Stage D Needs

`sbc_rag.py` will query:

```sql
SELECT chunk_text
FROM sbc_chunks
WHERE plan_id = :plan_id
ORDER BY embedding <=> :query_vector
LIMIT :top_k;
```

So `sbc_chunks` must be populated before Stage D can be written or tested.

---

## Chunking Strategy

```python
def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks
```

- `chunk_size=400` words ≈ 512 tokens for English prose
- `overlap=50` words preserves sentence context across boundaries
- Sections with fewer than `min_chunk_words` (20) are skipped with `logger.debug`

---

## Rate-Limit Handling (Voyage free tier)

Free tier: **3 RPM, 10K TPM** (no payment method on file).

- `voyage_batch_size=3` chunks per API call (~1 500 tokens/request)
- `voyage_sleep_s=22` seconds between requests (22 s × 3 = 66 s/min < 60 s window
  with headroom)
- `last_embed_time` dict passed across PDFs so the inter-PDF boundary also respects
  the sleep, not just the intra-PDF boundary
- Up to 3 retries with exponential backoff on a 429 response

---

## Script Responsibilities (`data/ingest/sbc_embed_ingest.py`)

1. Discover `*.pdf` files in `cfg.embed.sbc_dir`
2. Resolve `plan_id` from `plans.plan_marketing_name` via sidecar JSON from
   `sbc_manifest.yaml`; skip with WARNING if no match
3. Parse with `SBCParserRunner` or fall back to pdfplumber
4. Chunk each section's `raw_text`
5. Embed in batches via Voyage AI `voyage-4-large` with rate-limit sleep + retry
6. `INSERT ... ON CONFLICT (plan_id, source_file, section_name, chunk_index) DO NOTHING`
7. Write one `audit_log` row per PDF (SHA-256 of PDF bytes)

---

## Hydra Config (`data/ingest/configs/sbc_embed_ingest.yaml`)

```yaml
embed:
  sbc_dir: "data/raw/sbcs"
  chunk_size: 400
  overlap: 50
  min_chunk_words: 20
  voyage_model: "voyage-4-large"
  voyage_batch_size: 3        # free-tier safe (3 RPM)
  voyage_sleep_s: 22.0        # seconds between API calls
  database_url: ${oc.env:DATABASE_URL,postgresql://claimvoice:changeme@localhost:5432/claimvoice}
  voyage_api_key: ${oc.env:VOYAGE_API_KEY,""}
```

Override at CLI: `python data/ingest/sbc_embed_ingest.py embed.voyage_batch_size=10`

---

## SBC Manifest (`data/ingest/configs/sbc_manifest.yaml`)

Updated to use NYC OLR government-hosted PDFs (original insurer CDN URLs returned 404):

```yaml
sbcs:
  output_dir: "data/raw/sbcs"
  plans:
    - url: "https://www.nyc.gov/assets/olr/downloads/pdf/health/sbcs25-26/..."
      payor: "aetna"
      plan_name: "Aetna EPO Basic Plan"
      plan_year: 2026
    # ... 3 more plans
```

The `plan_name` values must match `plans.plan_marketing_name` (case-insensitive).

---

## DVC Stage (`dvc.yaml`)

```yaml
sbc_embed:
  cmd: python data/ingest/sbc_embed_ingest.py
  deps:
    - data/ingest/sbc_embed_ingest.py
    - data/ingest/configs/sbc_embed_ingest.yaml
    - data/raw/sbcs
  params:
    - data/ingest/configs/sbc_embed_ingest.yaml:
        - embed.chunk_size
        - embed.overlap
        - embed.voyage_model
```

No `outs:` — output is a database table. DVC re-runs whenever chunking params or
source PDFs change.

---

## Files Changed

| Action | Path |
|---|---|
| CREATE | `data/ingest/sbc_embed_ingest.py` |
| CREATE | `data/ingest/configs/sbc_embed_ingest.yaml` |
| MODIFY | `data/ingest/configs/sbc_manifest.yaml` — NYC OLR URLs |
| MODIFY | `dvc.yaml` — add `sbc_embed` stage |

---

## Acceptance Criteria

- `python data/ingest/sbc_embed_ingest.py` completes without error on all 4 NYC SBC PDFs.
- `SELECT COUNT(*) FROM sbc_chunks` returns 32 rows (4 plans × avg 8 chunks).
- `SELECT pg_size_pretty(pg_total_relation_size('sbc_chunks'))` returns ~776 kB.
- Re-running produces no new rows (`ON CONFLICT DO NOTHING`).
- One `audit_log` row per PDF with correct `data_hash`.
