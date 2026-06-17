# Component 15 - Inbound + Outbound Call Flows + Runbook - Plan

1. Rewrite `src/twilio/voice.ts` to emit `<Connect><Stream/></Connect>`
   pointing at `/media-stream`.
2. `src/twilio/outbound.ts` wraps Twilio's `calls.create` with our config.
3. `src/api/v1/call.ts` registers POST `/api/v1/voice/call` with zod validation.
4. Update `server.ts` to register the new API.
5. Update `lib/config.ts` to add `PUBLIC_BASE_URL` and S3/master-key envs.
6. Write `docs/runbook.md` with setup + demo + troubleshooting.

