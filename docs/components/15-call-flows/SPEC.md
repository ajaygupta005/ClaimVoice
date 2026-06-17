# Component 15 - Inbound + Outbound Call Flows + Runbook

> **Branch**: `feat/telephony-call-flows` | **Day(s)**: 19-20 | **Workstream**: WS-7

## Goal

Real inbound and outbound call flows wired to Media Streams. Operational
runbook for the demo.

- Inbound: TwiML response that plays greeting + consent + connects to
  Media Streams.
- Outbound: POST `/api/v1/voice/call { to, memberId }` triggers a Twilio
  `calls.create` with our voice webhook URL and a status callback.
- Runbook: how to set up Twilio webhook URLs (ngrok for local), demo flows,
  common issues, rollback.

