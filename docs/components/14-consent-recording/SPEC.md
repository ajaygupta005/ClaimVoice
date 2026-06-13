# Component 14 - State-Aware Consent + Encrypted Recording

> **Branch**: `feat/telephony-consent-recording` | **Day(s)**: 17, 21 | **Workstream**: WS-7

## Goal

When recording a call we must:

1. Detect whether the caller is in a two-party-consent state.
2. Play a recording notice TwiML before bridging if yes.
3. Encrypt the recording with AES-256-GCM. Per-call key wrapped under a
   per-tenant master key.
4. Upload to MinIO/S3.

## Two-party states

CA, CT, DE, FL, IL, MD, MA, MT, NH, OR, PA, WA (federal law is one-party).

## Out of scope

- Wiring the recording sink to the actual audio stream (we have the helpers
  in place; the audio capture is component 15+).
- Multi-tenant master key management.

