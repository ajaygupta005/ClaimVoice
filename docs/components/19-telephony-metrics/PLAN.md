# Component 19 - Telephony Metrics + Hardening - Plan

1. `src/lib/metrics.ts` — prom-client registry + counters/histograms/gauge.
2. `/metrics` endpoint in `server.ts`.
3. Integrate metrics into `twilio_ws/handler.ts` with a single-shot `finalize()`.
4. Instrument `recording/storage.ts` upload timing.
5. Add `prom-client` dep.
6. `tests/unit/metrics.test.ts`.
