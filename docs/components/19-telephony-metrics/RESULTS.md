# Component 19 - Telephony Metrics + Hardening - Results

- [ ] `pnpm --filter @claimvoice/telephony test` passes.
- [ ] `tsc --noEmit` clean.
- [ ] `/metrics` returns `telephony_*` series.

Commit:
```
git add services/telephony/src/lib/metrics.ts services/telephony/src/server.ts services/telephony/src/twilio_ws/handler.ts services/telephony/src/recording/storage.ts services/telephony/package.json services/telephony/tests/unit/metrics.test.ts docs/components/19-telephony-metrics/
git commit -m "feat(telephony): prometheus metrics and idempotent call finalization"
```
