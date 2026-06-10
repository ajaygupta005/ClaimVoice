# Component 02 - Data Layer - Results

## Checklist
- [ ] `docker compose up -d` brings up all three services
- [ ] `pg_isready -h localhost -p 5432` says ready
- [ ] `redis-cli -h localhost ping` returns PONG
- [ ] `curl localhost:9000/minio/health/live` returns 200
- [ ] `psql ... -c "SELECT extname FROM pg_extension"` shows vector and postgis

## Files in this commit
- `docker-compose.yml`
- `infra/postgres/init.sql`
- `infra/redis/redis.conf`
- `.env.example`
- `scripts/healthcheck.sh`

## Commit
```
git add docker-compose.yml infra/postgres/init.sql infra/redis/redis.conf .env.example scripts/healthcheck.sh tests/infra/ docs/components/02-data-layer/
git commit -m "chore(infra): docker compose with postgres pgvector postgis redis minio"
```

## Notes
-
