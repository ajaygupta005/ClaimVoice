#!/usr/bin/env bash
echo "Postgres:"
pg_isready -h localhost -p 5432 || echo "  not ready"

echo "Redis:"
redis-cli -h localhost ping || echo "  not ready"

echo "MinIO:"
curl -sf http://localhost:9000/minio/health/live > /dev/null && echo "  ok" || echo "  not ready"
