#!/usr/bin/env bash
set -euo pipefail
echo "Postgres:" && pg_isready -h localhost -p 5432 || true
echo "Redis:"    && redis-cli -h localhost ping  || true
echo "MinIO:"    && curl -s http://localhost:9000/minio/health/live || true
echo "MLflow:"   && curl -s http://localhost:5000 -o /dev/null -w "%{http_code}\n" || true
echo "Langfuse:" && curl -s http://localhost:3001 -o /dev/null -w "%{http_code}\n" || true
