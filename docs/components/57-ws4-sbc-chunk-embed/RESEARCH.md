# Component 40 — WS-4 SBC Chunk & Embed — Research

> Alternatives considered, decisions made, and key discussions that shaped the SPEC.

---

## Why pgvector inside Postgres — not a dedicated vector database

Supabase, Pinecone, Qdrant, and Weaviate were all raised as alternatives. The project
rejected them for three reasons:

1. **Transactional consistency.** The `sbc_chunks` table has a FK to `plans`. If a plan
   is deleted, its chunks cascade-delete automatically. In a separate vector store that
   guarantee disappears — you need a separate cleanup job and risk drift.

2. **One fewer system to operate.** The stack already runs Postgres, Redis, MinIO,
   Langfuse, MLflow, Prometheus, and Grafana. Adding a dedicated vector DB adds another
   container, another port, another secret, and another failure mode for a corpus of
   ~100 rows.

3. **Free, self-hosted, zero per-vector pricing.** pgvector is an extension — it costs
   nothing and the HNSW index fits entirely in memory at this corpus size.

Supabase specifically was raised and confirmed absent from the project. It would give
managed Postgres + pgvector, but the project runs everything self-hosted (Docker Compose)
to keep the 30-day cash cost at $0–$30. See ADR-0005.

---

## Why HNSW over IVFFlat

Both are pgvector index types. IVFFlat was considered but rejected:

- IVFFlat requires a `VACUUM ANALYZE` pass after bulk inserts before it is effective.
  HNSW is query-ready immediately after insert.
- IVFFlat recall drops at low `nprobe` values. Our `top_k` is 5 — we need high recall
  at small result sets.
- IVFFlat needs a training step (`lists` parameter tuned to corpus size). At ~100 rows,
  the correct value of `lists` is 1, which degrades to a flat scan. HNSW has no such
  degenerate case.

Chosen parameters: `m=16, ef_construction=64` — the pgvector defaults, appropriate for
a small corpus. Larger values would improve recall marginally at the cost of index build
time and memory, neither of which is a constraint here.

---

## Why vector(1024) — not 2048

voyage-4-large supports 2048, 1024, 512, and 256 dimensions via Matryoshka
Representation Learning (MRL). 2048 was considered for maximum accuracy.

Decision: **stay at 1024** because:

- The earlier voyage-3-large spec also used 1024. Keeping the same dimension means the
  Alembic migration and the HNSW index are unchanged — no additional work.
- At ~100 chunks the accuracy difference between 1024 and 2048 dims is negligible. MRL
  accuracy degrades meaningfully only when truncating below 512.
- Storage impact of 2048 dims: 2× the vector column size (~8 KB/row vs ~4 KB/row).
  Irrelevant at this scale but not a reason to add complexity.

If the corpus grows substantially (thousands of plans), revisiting 2048 is reasonable.

---

## Why voyage-4-large — not voyage-3-large

The original project spec locked in `voyage-3-large`. During SPEC authoring it was
confirmed that Voyage AI released the voyage-4 series in January 2026:

- voyage-4-large uses a Mixture-of-Experts (MoE) architecture and is now the top model
  on the RTEB leaderboard, superseding voyage-3-large.
- The free tier for the voyage-4 series increased from 50M to **200M tokens/month** —
  4× more generous than the model being replaced.
- voyage-4-large is 40% cheaper than comparable dense models at paid tier.

Since the corpus only needs ~30K tokens to embed (100 chunks × ~300 tokens), either
model would fit comfortably in the free tier. voyage-4-large was chosen for accuracy.

`voyage-4` (mid-tier) was also considered. Rejected in favour of voyage-4-large because
the hallucination guard downstream relies on retrieval quality — accuracy matters more
than the marginal latency difference between the two models at embedding time.

---

## Why a standalone ingest script — not embedding at parse time

An alternative design embeds chunks immediately inside `sbc_download.py` or
`SBCParserRunner` itself. Rejected because:

- `SBCParserRunner` (WS-3) is a Document AI component — it should know nothing about
  Voyage AI or the eligibility database. Cross-workstream contamination.
- `sbc_download.py` (WS-1) only moves files to disk. Adding embedding would break the
  single-responsibility of that script and make it depend on a network API.
- A standalone `sbc_embed_ingest.py` (WS-4) is idempotent, DVC-tracked independently,
  and can be re-run cheaply if chunking parameters change without re-downloading PDFs.

## Where the embeddings are stored

This was confirmed explicitly: `sbc_chunks` rows (including the `vector(1024)` column)
live in the **same PostgreSQL 16 Docker container** as all other project tables.
There is no separate vector database, no MinIO involvement, and no Redis caching for
the vectors themselves. pgvector stores and indexes them natively.

The data flow is:
```
data/raw/sbcs/*.pdf  →  SBCParserRunner (RAM)  →  Voyage API (network)  →  sbc_chunks (Postgres)
```

Nothing is persisted to disk at intermediate stages. The only durable output is the
Postgres table.

---

## Corpus size and storage estimate

Calculated from first principles during SPEC review:

- 8 PDFs × ~9 chunks/PDF = ~72–100 rows
- Per row: 4,096 bytes (vector) + ~2,200 bytes (text) + ~200 bytes (metadata) ≈ 6.5 KB
- Total table + HNSW index: **< 2 MB**
- Voyage API tokens to embed full corpus: ~30,000 — well under 0.02% of the 200M/month
  free tier

Storage is not a constraint at this scale. The `in_network` MRF table (sourced from
100+ GB files) dwarfs the vector store by orders of magnitude.

---

## References

- Voyage AI voyage-4 release: https://blog.voyageai.com/2026/01/15/voyage-4/
- voyage-4-large MoE deep dive: https://blog.voyageai.com/2026/03/03/moe-voyage-4-large/
- Voyage AI pricing: https://docs.voyageai.com/docs/pricing
- pgvector HNSW: https://github.com/pgvector/pgvector#hnsw
- ADR-0005 (Postgres as vector store): `docs/adr/0005-postgres-as-vector-store.md`
