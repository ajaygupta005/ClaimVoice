# SPEC-1 — Postgres Infrastructure (pgvector + PostGIS)

> **Commit**: `chore(infra): extend postgres image with pgvector for PostGIS+vector coexistence`

---

## Problem

The `postgis/postgis:16-3.4` base image ships PostGIS but **not pgvector**. The
`vector` PostgreSQL extension (`vector.control`) is absent from the image, so any
`CREATE EXTENSION IF NOT EXISTS vector` call fails:

```
ERROR: extension "vector" is not available
DETAIL: Could not open file "$libdir/vector.control": No such file or directory
```

This blocks migration 002 and any `sbc_chunks` write from day one.

## Solution

A thin custom Docker image extending the PostGIS base with the
`postgresql-16-pgvector` apt package:

**`infra/postgres/Dockerfile`**
```dockerfile
FROM postgis/postgis:16-3.4
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*
```

`docker-compose.yml` is updated to build from this Dockerfile instead of
pulling the stock image:

```yaml
# Before
postgres:
  image: postgis/postgis:16-3.4

# After
postgres:
  build: ./infra/postgres
```

## Why not use a different base image?

`ankane/pgvector` (the canonical pgvector image) does not include PostGIS. We
need both extensions simultaneously — `postgis` for `providers.location` geo-queries
and `vector` for `sbc_chunks` embeddings. The only clean path is extending the
PostGIS image with the pgvector apt package for Postgres 16.

## Verification

```bash
docker compose build postgres
docker compose up -d postgres
docker exec <container> psql -U claimvoice -d claimvoice \
  -c "SELECT name FROM pg_available_extensions WHERE name IN ('postgis','vector');"
# Expected: 2 rows
```
