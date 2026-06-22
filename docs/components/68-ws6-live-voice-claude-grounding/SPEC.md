# Component 68 - WS-6 Live Voice: Claude Grounding & Robustness

> **Branch**: feat/live-product | **Workstream**: WS-6 | **Plan phase**: 2-3

## Goal

Make the live voice loop produce grounded, Claude-composed answers for coverage / cost /
provider, and harden the brittle spots found during live verification.

- Feed the structured + SBC `tool_facts` into the Claude composer (not just the
  concatenated `tool_result`), so answers can cite exact figures and SBC passages.
- Make `estimate_cost` robust to STT variants ("deduction" for "deductible").
- Give `check_coverage` enough timeout headroom for the SBC-enriched `/coverage`.
- Verify the end-to-end grounded chain and the deterministic eval gate.

## Out of scope

- The browser proxy / UI (Component 69).
- Server-side Deepgram STT in the browser (browser Web Speech is the input path; Deepgram
  is validated and remains the telephony engine).
