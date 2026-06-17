# Component 12 - Telephony Service Scaffold + ARCHITECTURE.md

> **Branch**: `feat/telephony-scaffold-and-arch`  |  **Day(s)**: 14  |  **Workstream**: WS-7/WS-8

## Goal & Scope

Two related deliverables that wrap Phase 2 for WS-7 + WS-8.

### A. Telephony service scaffold
Fastify service on port 8005 with Twilio webhook endpoints.

**Endpoints**:
- `POST /twilio/voice` returns minimal TwiML.
- `POST /twilio/status` logs CallSid + status via shared-logging.
- `GET /health`.

**Config**: validated via zod at boot. Missing env = fail fast.

### B. ARCHITECTURE.md final pass
The system architecture document at repo root.

**Contents**:
- Full Mermaid block diagram.
- ASCII diagram alternative.
- Per-service responsibility table.
- Cross-cutting concerns (logging, observability, eval).
- Links to all ADRs.
- Production-gaps section (honest list of what we did not build).

