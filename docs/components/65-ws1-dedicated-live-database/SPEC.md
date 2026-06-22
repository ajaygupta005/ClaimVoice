# Component 65 - WS-1 Dedicated Live Database

> **Branch**: feat/live-product | **Workstream**: WS-1 (data/infra) | **Plan phase**: 0

## Goal

Stand up a dedicated, reproducible Postgres for the live product so every DB-backed
feature (coverage, cost, providers, SBC RAG) runs against one instance that has both
extensions:

- Build the combined **PostGIS + pgvector** image from `infra/postgres/Dockerfile` and run
  it on host port **5433** (the dev box already runs another app's Postgres on 5432, so the
  two coexist without a collision).
- `alembic upgrade head` applies `001_init_schema` (plan graph + providers with a PostGIS
  `geography` location) and `002_sbc_chunks` (pgvector(1024) + HNSW).
- Seed providers (+ enrichment), 16 plans / benefits / formulary / codes, members, the demo
  member `CVX-0042-MT` (plan "ClaimVoice Demo PPO", golden values), and 6 cardiology
  providers near Midtown so "find a cardiologist" returns results.
- `.env` carries the run-mode toggles + service URLs (gitignored).

## Out of scope

- Reusing another app's Postgres (the previous dev workaround) -- superseded here.
- Full-scale CMS ingestion (the synthetic seed covers the demo).
- SBC embedding / ingest itself (Component 66).
