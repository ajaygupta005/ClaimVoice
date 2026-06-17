# Component 30 - WS-2 Voice Agent UI Layout - Implementation Plan

## Inspect

1. [ ] Read `apps/web/src/components/VoiceAssistantUI.tsx`.
2. [ ] Read `apps/web/src/lib/mock-data.ts`.
3. [ ] Open `/dashboard/voice`.
4. [ ] Review current dashboard shell width and spacing.

## Layout Changes

5. [ ] Keep `VoiceAssistantUI` as the main component.
6. [ ] Keep latest answer near the top.
7. [ ] Replace the current right-side vertical pipeline layout.
8. [ ] Create a main conversation row with two side-by-side panels:
   - left: Agent Talk
   - right: Transcript
9. [ ] Move transcript out from below Agent Talk.
10. [ ] Keep typed input with Agent Talk, below the mic area.
11. [ ] Add responsive sizing so Agent Talk and Transcript use the available width well.
12. [ ] Make transcript scroll inside its own panel when needed.

## Horizontal Pipeline

13. [ ] Move agent pipeline below the Agent Talk + Transcript row.
14. [ ] Render pipeline as a horizontal left-to-right sequence.
15. [ ] Include these steps:
   - Identify member
   - Understand question
   - Check coverage / formulary / provider
   - Hallucination guard
   - Prepare response
16. [ ] Show completed/running/pending states.
17. [ ] Use compact connectors or lines between steps.
18. [ ] Make the pipeline span the conversation area width.

## Backend Connections

19. [ ] Move backend connections away from the main content.
20. [ ] Render backend connections as a compact far-right rail or narrow panel.
21. [ ] Use small LED dots instead of large cards/badges.
22. [ ] Keep labels short.
23. [ ] Make it visually secondary.

## Behavior

24. [ ] Keep push-to-talk mock behavior unchanged.
25. [ ] Keep typed input mock behavior unchanged.
26. [ ] Do not add real backend calls.
27. [ ] Do not change mock agent answer logic.
28. [ ] Do not change voice-agent backend code.

## Responsive Behavior

29. [ ] On laptop/desktop, Agent Talk and Transcript must be side by side.
30. [ ] On smaller screens, stacking is acceptable only if needed.
31. [ ] Backend rail should not overlap main content.

## Verify

32. [ ] Run web typecheck.
33. [ ] Open `/dashboard/voice`.
34. [ ] Confirm Agent Talk and Transcript are side by side.
35. [ ] Confirm pipeline is horizontal below both panels.
36. [ ] Confirm backend connections are compact and far right.
37. [ ] Confirm dark mode works.
38. [ ] Confirm push-to-talk and typed input still work.

## Commit

39. [ ] Stage only UI/docs files for Component 30.
40. [ ] Commit with:

```bash
git commit -m "feat(web): refine voice agent UI layout"