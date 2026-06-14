# Component 21 - WS-2 Browser Voice UI - Implementation Plan

> Step-by-step. Check off as you go.

### Inspect
1. [ ] Read `eval/datasets/golden_qa.json`.
2. [ ] Read `docs/components/16-halluc-and-coverage-eval/SPEC.md`.
3. [ ] Read `apps/web/src/components/VoiceChat.tsx`.
4. [ ] Read `apps/web/src/app/dashboard/voice/page.tsx`.
5. [ ] Review Card, Plan, and Providers styling.

### Mock data
6. [ ] Add mock voice transcript data to `mock-data.ts`.
7. [ ] Add mock assistant answer based on golden QA examples.
8. [ ] Add mock tool/safety stages: identify member, check coverage, find provider, fact-check answer.
9. [ ] Add status values for STT, TTS, and backend bridge.

### UI
10. [ ] Replace Voice placeholder with voice UI.
11. [ ] Add latest answer card near the top.
12. [ ] Add push-to-talk panel.
13. [ ] Add typed fallback input.
14. [ ] Add transcript panel.
15. [ ] Add tool/safety stage panel.
16. [ ] Keep transcript readable without excessive scrolling.

### Behavior
17. [ ] Push-to-talk can toggle a local mock listening state.
18. [ ] Typed fallback can append a mock member message.
19. [ ] Ask button can append a mock assistant answer.
20. [ ] No backend call is required.

### Verify
21. [ ] Run `pnpm --filter @claimvoice/web typecheck`.
22. [ ] Open `/dashboard/voice`.
23. [ ] Confirm transcript renders.
24. [ ] Confirm push-to-talk toggles state.
25. [ ] Confirm typed fallback works.
26. [ ] Confirm tool/safety stages are visible.

### Commit
27. [ ] Stage only frontend voice-view files and this component docs.
28. [ ] Commit with: