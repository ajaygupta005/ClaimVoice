# telephony

Fastify service that talks to Twilio. Eventually bridges Twilio Media Streams
to the voice-agent service.

## Dev

```
cp ../../.env.example .env
pnpm install
pnpm dev
```

The service listens on `:8005`. Twilio webhook URLs:
- `POST /twilio/voice` — answers incoming calls
- `POST /twilio/status` — receives call status updates

## Point a Twilio number at it

For local testing, expose the service via ngrok:

```
ngrok http 8005
```

Then in Twilio Console, set the phone number's Voice webhook to:
`https://<your-ngrok>.ngrok.io/twilio/voice`
