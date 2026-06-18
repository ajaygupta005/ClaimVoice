# Compliance — HIPAA Design Notes

ClaimVoice handles Protected Health Information (PHI): insurance member IDs,
dates of birth, plan and coverage details, and recorded voice. This document
records how the architecture is designed for HIPAA, and what is stubbed in the
current build versus what production would add.

## Principle: structured data decides, the LLM narrates

No coverage or cost statement is ever spoken unless it is grounded in the
structured plan data. The hallucination guard
(`services/voice-agent/src/voice_agent/guards/`) fact-checks every claim before
text-to-speech. This is the single most important control for avoiding
incorrect coverage statements, which carry both clinical and legal risk.

## BAA-eligible vendors only on PHI paths

Every third party that can see PHI must have a signed Business Associate
Agreement. The build is designed so PHI only flows to BAA-eligible services:

| Vendor | Role | PHI exposure | BAA path |
| --- | --- | --- | --- |
| Anthropic Claude | LLM | Yes (plan context) | Enterprise tier offers a BAA |
| Deepgram | Speech-to-text | Yes (caller audio) | BAA available |
| Cartesia | Text-to-speech | Synthesized speech only | BAA available |
| Twilio | Telephony | Yes (call audio) | BAA available |
| AWS / MinIO | Storage | Yes (encrypted at rest) | AWS BAA; self-hosted MinIO under our control |

Voyage AI (embeddings) only sees plan-document text (not member PII) and is
kept off the PHI path.

## Telephony controls (WS-7)

- **State-aware consent** (`services/telephony/src/recording/consent.ts`):
  callers in two-party-consent states (CA, CT, DE, FL, IL, MD, MA, MT, NH, OR,
  PA, WA) hear a recording notice before the call is bridged. Unknown states
  default to playing the notice (safer).
- **Encrypted recordings** (`recording/crypto.ts`): AES-256-GCM with a random
  per-call key, wrapped under a per-tenant master key. Plaintext audio is never
  persisted. Decryption needs both the ciphertext (MinIO) and the wrapped key.
- **PII redaction in logs** (`packages/shared-logging`): `member_id`, `dob`,
  `name`, `phone`, `address`, `ssn`, `email` are redacted before any log line
  is emitted, in both the Node (pino) and Python (loguru) loggers.

## Audit logging

Every coverage statement is written to an immutable `audit_log` (insert-only)
with the claim text, the source rows it was grounded in, a hashed member id,
and a trace id. This supports after-the-fact review of what the agent told a
member and why.

## Observability and PHI

Langfuse traces capture prompts and responses, which can contain PHI. Langfuse
is **self-hosted** (not the SaaS) specifically so traces stay inside our
perimeter. Prometheus and Grafana only see numeric metrics — never PHI.

## What is stubbed in this build

| Area | Build | Production |
| --- | --- | --- |
| Eligibility (X12 270/271) | Hand-crafted stub responses | Availity / Change Healthcare / Stedi under BAA |
| Card images | 100 synthetic cards | Real member uploads with encryption in transit and at rest |
| Master key | `MASTER_KEY_HEX` env var | KMS / HSM-backed key management with rotation |
| Identity verification | DOB + ZIP | Step-up auth (OTP) for sensitive actions |
| BAAs | Not signed | Signed with every vendor above before any real PHI |

## Retention

Call recordings and audit logs have jurisdiction-specific retention
requirements. The build stores recordings indefinitely in MinIO; production
must implement a retention schedule and legal hold per state and per payer
contract.
