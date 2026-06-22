# Component 54 - WS-2/WS-7 Gemini Runtime Tests and Fallbacks - Implementation Plan

## Inspect

1. [ ] Read Components 50-53 implementation.
2. [ ] Read existing voice-agent tests.
3. [ ] Read existing frontend voice UI behavior.
4. [ ] Read local startup logs for voice-agent and web.

## Backend Tests

5. [ ] Test missing Gemini key.
6. [ ] Test Gemini bridge connection failure.
7. [ ] Test transcript event normalization.
8. [ ] Test speech event normalization.
9. [ ] Test close is safe after failure.
10. [ ] Test no secret leakage in status responses.

## Frontend Tests / Manual Checks

11. [ ] Test mic permission denied.
12. [ ] Test short speech question.
13. [ ] Test long speech question.
14. [ ] Test interrupt during listening.
15. [ ] Test interrupt during speaking.
16. [ ] Test Gemini unavailable fallback.
17. [ ] Test browser route change cleanup.

## Recovery Behavior

18. [ ] Add timeout constants in one place.
19. [ ] Add no-transcript recovery.
20. [ ] Add no-agent-response recovery.
21. [ ] Add no-playback-start recovery.
22. [ ] Add no-playback-end recovery.
23. [ ] Always return to `Ready` or `Error - retry`.

## Observability

24. [ ] Add runtime debug logs without secrets.
25. [ ] Add status panel fallback reasons.
26. [ ] Add browser console logs only behind a debug flag.
27. [ ] Keep member-facing UI clean.

## Run

28. [ ] Run voice-agent tests.
29. [ ] Run web build or typecheck.
30. [ ] Run manual Chrome voice demo.
31. [ ] Record known limitations.