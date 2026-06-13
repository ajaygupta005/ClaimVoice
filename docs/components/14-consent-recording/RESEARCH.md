# Component 14 - State-Aware Consent + Encrypted Recording - Research

## Why AES-GCM
- Authenticated encryption (we get tamper detection for free).
- Node ships it in `node:crypto`. No extra dependencies.

## Per-call key vs single-tenant key
A per-call random key plus a wrapped key blob means a leaked call doesn't
compromise the entire recording corpus. Standard pattern for E2EE.

## Area-code-to-state lookup
NANPA assigns area codes to states. For the project we ship a hand-picked
subset covering most major metros. Production would ingest the full file
from nationalnanpa.com nightly.

