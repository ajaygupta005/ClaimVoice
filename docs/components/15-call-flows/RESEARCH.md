# Component 15 - Inbound + Outbound Call Flows + Runbook - Research

## TwiML inline vs Twilio Studio
TwiML in code stays in the repo, gets reviewed, gets unit-tested. Studio
flows are clicked-together in the Twilio UI and can't be diffed. We pick
inline.

## Outbound TCPA
Federal TCPA limits outbound calling to opted-in members. We assume the
member opted in by creating a ClaimVoice account; production would enforce
this explicitly.

## ngrok for local dev
Twilio webhooks need a public URL. ngrok is the standard local dev tunnel.
Free tier is fine for one-off demos.

