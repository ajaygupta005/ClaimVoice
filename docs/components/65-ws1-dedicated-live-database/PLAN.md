# Component 65 - WS-1 Dedicated Live Database - Plan

1. `docker-compose.yml`: point the `postgres` service at `build: ./infra/postgres`
   (combined PostGIS + pgvector) and map host port `5433:5432`. Set `.env`
   `DATABASE_URL=postgresql://claimvoice:changeme@localhost:5433/claimvoice`.
2. `docker compose up -d postgres` (first run builds the image; the base-image pull may
   need a retry).
3. Apply schema: `alembic upgrade head` in `services/eligibility` (`001` + `002_sbc_chunks`).
4. Seed via `scripts/seed_dev.ps1 -DatabaseUrl ...5433...`: generate NPPES sample ->
   `npi_ingest` -> `enrich_providers` -> `seed_dev` (plans/benefits/formulary/codes) ->
   `seed_test_members` -> `seed_demo_member`.
5. Add `data/ingest/seed_cardiology.sql` (6 synthetic cardiology providers near Midtown,
   `specialty_codes` including "Cardiologist"); load idempotently (`ON CONFLICT (npi)`).
6. Set the live run-mode env in `.env`: `TOOL_MODE=http`, `SBC_EMBED_PROVIDER=azure`,
   `STT_MODE=deepgram`, `TTS_MODE=cartesia`, and answer / fact-check `claude`.
