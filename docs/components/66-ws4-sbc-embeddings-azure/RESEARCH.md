# Component 66 - WS-4 SBC Embeddings on Azure OpenAI - Research

## Why Azure text-embedding-3-large over Voyage
The snapshotted SBC pipeline embedded with Voyage, but the available Voyage tier
rate-limited document ingest badly. An Azure OpenAI deployment (1M TPM / 1000 RPM) was on
hand and is independent of the chat model (Claude), so it carries embeddings without
touching answer generation. `text-embedding-3-large` is natively 3072-dim but supports the
`dimensions` parameter, so requesting 1024 keeps the existing `vector(1024)` migration +
HNSW index unchanged. The query and document sides share `lib/embeddings.py`, so they
always use the same model + dimension (a hard requirement for a shared vector index).

## Why a synthetic SBC corpus
The manifest's payor SBC URLs (constructed 2026 paths) return 404 / HTML, not PDFs. For an
offline-reproducible demo we generate deterministic synthetic SBCs (`gen_synthetic_sbcs.py`)
whose text covers real SBC sections (deductible, MRI prior-auth, Rx tiers, exclusions) so
retrieval returns relevant passages. The demo plan gets its own document so the demo member
is SBC-grounded; the rest map to seeded plans.

## Why CAST(:vec AS vector)
The snapshot's repo wrote `embedding <=> :query_vec::vector`. SQLAlchemy `text()` parses
`:name` bind params, and the `::vector` cast adjacent to `:query_vec` broke parsing (the
bind was not substituted -> syntax error). `CAST(:query_vec AS vector)` avoids the `::`
adjacency, so the 1024-dim query vector binds correctly.
