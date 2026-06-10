# Component 12 - Telephony Service Scaffold + ARCHITECTURE.md - Implementation Plan

> Step-by-step. Check off as you go.

### Telephony scaffold
1. [ ] Author `services/telephony/package.json` with fastify, @fastify/websocket, twilio, pino, zod, tsx, typescript.
2. [ ] Author `tsconfig.json` (target ES2022, strict, module esnext).
3. [ ] Author `Dockerfile` (Node 20 alpine, pnpm install, build, run).
4. [ ] Author `src/server.ts` (Fastify init, /health route, register twilio routes).
5. [ ] Author `src/twilio/voice.ts` returning a minimal TwiML response.
6. [ ] Author `src/twilio/status.ts` logging CallSid + status via shared-logging.
7. [ ] Author `src/lib/config.ts` with a zod schema for env validation.
8. [ ] Author `src/lib/logger.ts` wrapping pino from shared-logging.

### ARCHITECTURE.md
9. [ ] Author the full Mermaid block diagram at repo root in `ARCHITECTURE.md`.
10. [ ] Add the ASCII alternative.
11. [ ] Per-service responsibility table.
12. [ ] Cross-cutting concerns section.
13. [ ] Link out to every ADR.
14. [ ] Production-gaps section (honest list of stubs).

### Wrap
15. [ ] Run `pnpm --filter @claimvoice/telephony dev` to confirm service boots.
16. [ ] Curl `/health` and the two Twilio webhook routes.
17. [ ] Commit with message `feat(telephony): scaffold service with twilio webhooks + architecture md`.

