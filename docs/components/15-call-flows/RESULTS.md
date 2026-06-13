# Component 15 - Inbound + Outbound Call Flows + Runbook - Results

## Checklist

- [ ] Curl `localhost:8005/twilio/voice` returns TwiML with `<Stream>` URL.
- [ ] Curl `localhost:8005/api/v1/voice/call` with bad input returns 400.
- [ ] Curl with good input + Twilio creds returns `{callSid, status}`.
- [ ] Reading the runbook end-to-end someone unfamiliar can demo the inbound flow.

## Commit

```
git add services/telephony/src/twilio/ \
        services/telephony/src/api/ \
        services/telephony/src/server.ts \
        services/telephony/src/lib/config.ts \
        services/telephony/tests/unit/call_schema.test.ts \
        docs/runbook.md \
        docs/components/15-call-flows/

git commit -m "feat(telephony): inbound and outbound call flows with runbook"
```

## Notes
-

