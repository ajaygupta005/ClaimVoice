# Component 66 - WS-4 SBC Embeddings on Azure OpenAI

> **Branch**: feat/live-product | **Workstream**: WS-4 | **Plan phase**: 1

## Goal

Run the SBC RAG index on **Azure OpenAI `text-embedding-3-large` @ 1024 dims** instead of
Voyage (the snapshotted pipeline's default), because the available Voyage tier rate-limits
hard and an Azure deployment (1M TPM / 1000 RPM) was on hand.

- Provider-dispatched embedding behind `SBC_EMBED_PROVIDER` (default `azure`, Voyage as the
  fallback), used identically on the ingest (document) side and the RAG query side.
- Keep the `vector(1024)` column unchanged by requesting `dimensions=1024` from the model.
- Build the SBC corpus: the real payor SBC URLs 404, so generate 8 deterministic synthetic
  SBC PDFs, map them to seeded plans (one to the demo plan), and ingest into `sbc_chunks`.

## Out of scope

- The `/coverage` grounding wiring that consumes the index (Component 67).
- Changing the migration / embedding dimension (stays 1024).
