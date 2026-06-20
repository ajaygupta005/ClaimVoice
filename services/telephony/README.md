# telephony

Fastify service that talks to Twilio. Eventually bridges Twilio Media Streams
to the voice-agent service.

## Dev

```
cp ../../.env.example .env
pnpm install
pnpm dev
```

The service listens on `:8005`. Endpoints:
- `POST /twilio/voice` — answers incoming calls
- `POST /twilio/status` — receives call status updates
- `POST /api/v1/voice/call` — places an outbound call (rate limited to 5 per minute)
- `GET /health` — liveness probe
- `GET /metrics` — Prometheus metrics (scraped by the telephony target)

## Metrics

Exposed at `GET /metrics` and scraped into the Voice/Telephony Grafana
dashboard. Series include `telephony_calls_total`,
`telephony_call_duration_seconds`, `telephony_active_calls`,
`telephony_audio_bytes_total`, `telephony_recording_upload_seconds`, and
`telephony_outbound_call_requests_total`.

## Point a Twilio number at it

For local testing, expose the service via ngrok:

```
ngrok http 8005
```

Then in Twilio Console, set the phone number's Voice webhook to:
`https://<your-ngrok>.ngrok.io/twilio/voice`
