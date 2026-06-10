# Component 02 - Data Layer Infrastructure - Results

> Fill in as work progresses. This becomes the evidence the work is done.

## Verification checklist
- [ ] `docker compose up -d` brings everything to healthy state
- [ ] `pg_isready -h localhost -p 5432` returns ready
- [ ] `redis-cli -h localhost ping` returns PONG
- [ ] `curl localhost:9000/minio/health/live` returns 200
- [ ] `psql -c "SELECT extname FROM pg_extension"` lists vector + postgis
- [ ] Bring down + up; data in Postgres persists (named volume working)
- [ ] Bring down + up; data in MinIO persists

## Metrics
- Total docker-compose startup time: __ s
- Memory footprint of all three services: __ MB

## Notes / surprises
-

## Follow-ups
-

