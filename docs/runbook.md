# Runbook

How to operate ClaimVoice in dev and demo.

## Bring up the stack

```bash
cp .env.example .env
just install
just up
just dev
```

Confirm services:

| Service | URL |
| --- | --- |
| Web | http://localhost:3000 |
| API gateway | http://localhost:8080 |
| Telephony | http://localhost:8005 |
| MLflow | http://localhost:5000 |
| Langfuse | http://localhost:3001 |
| Grafana | http://localhost:3002 |

## Twilio webhook setup

For local testing, expose the telephony service via ngrok:

```bash
ngrok http 8005
```

In the Twilio Console, set your phone number's **Voice URL** to:

```
https://<your-ngrok-id>.ngrok.io/twilio/voice
```

And **Status Callback URL** to:

```
https://<your-ngrok-id>.ngrok.io/twilio/status
```

Test by calling the number. You should hear the greeting and the call should
appear in the telephony service logs.

## Demo flows

### Inbound

1. Call the Twilio number.
2. You hear: "Hello, this is ClaimVoice. How can I help you today?"
3. (If from a two-party-consent state) you also hear the recording notice.
4. The call connects to the voice agent over Media Streams.

### Outbound

```bash
curl -X POST http://localhost:8005/api/v1/voice/call \
  -H "Content-Type: application/json" \
  -d '{"to": "+12125551234", "memberId": "TEST123"}'
```

Returns `{ callSid, status }`.

## Common issues

| Symptom | Fix |
| --- | --- |
| Twilio webhook hits 404 | Confirm ngrok is running and webhook URL matches |
| `Twilio credentials not configured` | Set `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` in `.env` |
| Audio glitchy | Check sample-rate conversion in `audio_codec/resample.ts` |
| Recording not uploading | Confirm MinIO is up and `S3_*` env vars are set |
| CA call has no consent prompt | Check `state_lookup.ts` includes the area code |

## Rollback

If a deploy goes bad on demo day:

```bash
git revert <bad-sha>
git push origin main
```

CI redeploys automatically (if the deploy workflow is wired).
