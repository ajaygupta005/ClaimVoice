# Component 14 - State-Aware Consent + Encrypted Recording - Plan

1. `src/recording/state_lookup.ts` with area code -> state map.
2. `src/recording/consent.ts` with TwiML factory.
3. `src/recording/crypto.ts` using `node:crypto` AES-256-GCM.
4. `src/recording/storage.ts` uploads ciphertext + wrapped key to MinIO.
5. Add `@aws-sdk/client-s3` to `package.json` deps.
6. Unit tests for state lookup and crypto round-trip.

