# Component 19 - WS-2 Plan Details View - Implementation Plan

> Step-by-step. Check off as you go.

### Inspect
1. [ ] Read `eval/datasets/golden_qa.json`.
2. [ ] Read `apps/web/src/lib/mock-data.ts`.
3. [ ] Read `apps/web/src/app/dashboard/plan/page.tsx`.
4. [ ] Review Card tab styling for consistency.

### Mock data
5. [ ] Add plan summary mock data to `mock-data.ts`.
6. [ ] Add cost summary data: deductible, used amount, OOP max, copays.
7. [ ] Add coverage rows from golden QA examples.
8. [ ] Add prior authorization notes.
9. [ ] Add example questions from golden QA.

### UI
10. [ ] Replace Plan placeholder with real plan details screen.
11. [ ] Add member/plan summary section.
12. [ ] Add cost summary cards.
13. [ ] Add coverage highlights table/list.
14. [ ] Add prior authorization section.
15. [ ] Add example questions section.

### Verify
16. [ ] Run `pnpm --filter @claimvoice/web typecheck`.
17. [ ] Open `/dashboard/plan`.
18. [ ] Confirm the page renders inside the dashboard shell.
19. [ ] Confirm no backend service is required.

### Commit
20. [ ] Stage only frontend plan-view files and this component docs.
21. [ ] Commit with:

```bash
git commit -m "feat(web): add plan details view"