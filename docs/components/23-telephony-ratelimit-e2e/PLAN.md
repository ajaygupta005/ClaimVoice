# Component 23 - Telephony Rate Limit + E2E Dry Run - Plan

1. Register `@fastify/rate-limit` with `global: false` in `server.ts`.
2. Opt the outbound route into rate limiting in `api/v1/call.ts`.
3. Count rate-limited attempts via the error handler.
4. `tests/integration/e2e_dry_run.test.ts`.
5. Add `@fastify/rate-limit` dep.
