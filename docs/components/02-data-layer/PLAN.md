# Component 02 - Data Layer Infrastructure - Implementation Plan

> Step-by-step. Check off as you go.

1. [ ] Author `docker-compose.yml` with three services: postgres, redis, minio.
2. [ ] Author `infra/postgres/init.sql` with `CREATE EXTENSION IF NOT EXISTS vector;` and `CREATE EXTENSION IF NOT EXISTS postgis;`.
3. [ ] Wire `.env.example` with `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, `REDIS_URL`, `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`.
4. [ ] Author `infra/redis/redis.conf` (AOF off for dev, light memory limits).
5. [ ] Add health checks to each service (pg_isready, redis-cli ping, MinIO health endpoint).
6. [ ] Author `scripts/healthcheck.sh` that hits all three.
7. [ ] Document setup in `infra/postgres/README.md`, `infra/redis/README.md`, `infra/minio/README.md`.
8. [ ] Run `docker compose up -d` and verify everything is healthy.
9. [ ] Commit with message `chore(infra): docker-compose data layer with postgres pgvector postgis redis minio`.

