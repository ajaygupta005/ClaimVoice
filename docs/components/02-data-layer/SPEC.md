# Component 02 - Data Layer Infrastructure

> **Branch**: `chore/data-layer`  |  **Day(s)**: 1-2  |  **Workstream**: WS-7/WS-8

## Goal & Scope

`docker compose up -d` brings up the entire data layer for the project:
- **PostgreSQL 16** with **pgvector** (RAG embeddings) and **PostGIS** (provider geo) extensions on port 5432.
- **Redis 7** on port 6379 (sessions, cache, streaming buffers).
- **MinIO** S3-compatible object storage on ports 9000 (API) and 9001 (console).

**Configuration**:
- Postgres image: `postgis/postgis:16-3.4` (bundles both extensions in one image).
- Named volumes for Postgres + MinIO; Redis is ephemeral (cache only).
- Health checks for all three services.
- Ports exposed on localhost only.

**Env contract**: `.env.example` lists every required key.

**Out of scope**: MLflow, Langfuse, Prometheus, Grafana (separate components).

