# ADR 0005: PostgreSQL with pgvector as the single store

## Status

Accepted.

## Context

The eligibility service does retrieval over Summary-of-Benefits chunks (RAG)
and the providers service does geo-search over the NPI directory. We could run
a dedicated vector database (Qdrant, Weaviate, Pinecone) and a separate geo
store, or keep everything in Postgres.

## Decision

Use **PostgreSQL 16** as the single store, with the **pgvector** extension for
embeddings and **PostGIS** for provider geo-search.

## Reasons

- **One system to operate.** Plan graph, SBC embeddings, and provider geo all
  live in the same database with the same backups, migrations, and access
  control.
- **Transactional consistency.** A member record and its derived embeddings
  stay in sync in one transaction — no dual-write drift between Postgres and a
  separate vector DB.
- **Good enough at our scale.** pgvector with an HNSW index handles the SBC
  corpus comfortably; we are nowhere near the >10M-vector point where a
  dedicated engine starts to pay off.
- **Free and self-hosted.** No per-vector pricing.

## Consequences

- The SBC RAG service stores `voyage-3-large` embeddings in a `vector(1024)`
  column with an HNSW index.
- Migrations for vector and geo columns live alongside the rest of the schema
  in `services/eligibility/alembic/`.
- If retrieval volume grows past Postgres comfort, the embedding table can be
  lifted into Qdrant later without changing the application contract.

## Alternatives considered

- **Qdrant / Weaviate** — strong dedicated engines, but add a second system and
  break transactional consistency with the relational data.
- **Pinecone** — managed and easy, but SaaS-only and priced per vector.
