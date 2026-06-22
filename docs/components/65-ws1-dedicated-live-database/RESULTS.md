# Component 65 - WS-1 Dedicated Live Database - Results

## Checklist
- [x] docker-compose `postgres` builds `infra/postgres/Dockerfile` on host **5433**.
- [x] `alembic upgrade head` = `001` + `002_sbc_chunks` (verified `alembic_version=002`).
- [x] Seeded: 500 providers, 17 plans, 31 members incl. demo `CVX-0042-MT`
      (plan `ClaimVoice Demo PPO`, id `4bdc799f-...`).
- [x] `data/ingest/seed_cardiology.sql` -> 6 cardiology providers near Midtown.
- [x] Extensions present: `postgis`, `vector`.

## Verification
- `docker exec ... pg_isready` ok; `SELECT version_num FROM alembic_version` = 002.
- `/coverage`, `/cost/estimate`, `/providers/near` all return live DB data.
- Recovered the container twice after Docker Desktop stopped (`docker compose up -d
  postgres`); the `pg_data` volume persisted (sbc_chunks = 40 survived).

## Commit
```
01b11f9 feat(ws4): SBC RAG on Azure ... (docker-compose -> host port 5433)
07ee0fb feat(ws2,ws5): seed cardiology providers ...
```

## Notes
- `.env` (keys + run modes) is gitignored; `.env.example` carries placeholders.
- Keep Docker Desktop running -- if it stops, DB-backed calls hang until
  `docker compose up -d postgres` + a service restart.
