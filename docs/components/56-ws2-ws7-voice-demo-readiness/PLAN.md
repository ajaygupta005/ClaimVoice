# Component 56 - WS-2/WS-7 Voice Demo Readiness - Plan

## Phase 1 - Stabilize The Current Demo

1. [x] Keep browser STT as the default microphone path for the local browser demo.
2. [x] Keep Claude as the answer composer.
3. [x] Keep Cartesia Skylar as the default high-quality speakback path.
4. [x] Keep Gemini Live behind explicit developer-only flags.
5. [x] Show text answers immediately before audio playback finishes preparing.
6. [x] Add watchdogs so stuck voice states return to `Ready`.
7. [x] Add startup/runtime checks for voice dependencies and provider configuration.

## Phase 2 - Clean Demo Packaging

8. [ ] Add a one-command demo checklist to the project docs.
9. [ ] Add a known-good `.env.example` section for voice runtime variables without secrets.
10. [ ] Add a short demo script with 5-7 supported questions:
    - urgent care copay
    - MRI coverage and prior authorization
    - formulary drug lookup
    - in-network cardiologist lookup
    - denied claim escalation
11. [ ] Add a reset button for the voice transcript.
12. [ ] Add a visible but compact latency breakdown for one completed turn.

## Phase 3 - WS-2 Pending Work

13. [ ] Decide production STT path:
    - short term: browser STT for demo only
    - production option: Deepgram or Cartesia STT
14. [ ] Add clear microphone permission error states.
15. [ ] Test responsive layout on common laptop and tablet widths.
16. [ ] Keep backend connection indicators compact and secondary.
17. [ ] Add transcript export or copy-to-clipboard.
18. [ ] Add session reset and interrupt controls that are obvious during demos.
19. [ ] Add Playwright coverage for:
    - typed question
    - browser STT fallback path
    - TTS unavailable path
    - Cartesia configured path with mocked audio

## Phase 4 - WS-7 Pending Work

20. [ ] Make the LangGraph runtime the single source of truth for pipeline step state.
21. [ ] Expand tool contracts for:
    - member summary
    - plan benefits
    - formulary search
    - provider search
    - prior authorization rules
    - claims status
22. [ ] Ensure every Claude answer includes tool evidence before guard approval.
23. [ ] Add stronger guard categories:
    - grounded
    - partial
    - needs human
    - unsupported
    - safety escalation
24. [ ] Add turn-level logs:
    - transcript source
    - intent
    - tool calls
    - guard result
    - TTS provider
    - latency by stage
25. [ ] Add regression eval cases for realistic member support flows.
26. [ ] Add Twilio parity so phone calls use the same answer, guard, and Cartesia output contracts.

## Phase 5 - Cartesia Production Hardening

27. [ ] Keep API keys server-side only.
28. [ ] Add Cartesia request timeout, retry, and fallback metrics.
29. [ ] Cache or reuse short demo phrases only if allowed by product/privacy policy.
30. [ ] Move from full WAV generation to streaming TTS if latency remains noticeable.
31. [ ] Add tests for missing key, 401/403, 429, timeout, malformed audio, and playback abort.

## Phase 6 - Gemini Cleanup Decision

32. [ ] Keep Gemini code only as an experimental runtime while it is useful.
33. [ ] Hide Gemini from normal UI unless `NEXT_PUBLIC_ENABLE_GEMINI_TTS=1` or `NEXT_PUBLIC_ENABLE_GEMINI_STT=1`.
34. [ ] If not needed after Cartesia is stable, remove Gemini UI surface and keep only backend test docs or delete the runtime in a later cleanup component.

## Verification

35. [ ] Run voice-agent unit tests.
36. [ ] Run web typecheck.
37. [ ] Start the project with the normal startup script.
38. [ ] Confirm `/dashboard/voice` supports:
    - typed question
    - spoken question
    - immediate text answer
    - Cartesia Skylar audio speakback
    - return to `Ready`
39. [ ] Confirm no secrets appear in logs, runtime status responses, or browser console.
