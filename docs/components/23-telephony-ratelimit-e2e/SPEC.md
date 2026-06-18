# Component 23 - Telephony Rate Limit + E2E Dry Run

> Branch: `feat/telephony-ratelimit-e2e` | Day(s): 29-30 | Workstream: WS-7

Per-route rate limit on the outbound call API (5/min) so dialing can't be abused, plus an in-process e2e dry-run test that exercises /health, /metrics, /twilio/voice, outbound validation, and the rate limit. A real outbound call is only attempted when `DRY_RUN_REAL_CALL=1`.
