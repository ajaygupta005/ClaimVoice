# Component 60 - WS-2 Plan Details from Eligibility APIs Plan

## Implementation Steps

1. Review current Plan page data shape.
   - Identify all mock fields.
   - Map UI sections to backend fields.

2. Add Eligibility client methods.
   - `getMemberSummary(memberId)`
   - `getPlanBenefits(planId)`

3. Define active member source.
   - Use existing demo member only in demo mode.
   - Prepare for future authenticated member context.

4. Wire page data loading.
   - Fetch member summary.
   - Fetch plan benefits from returned plan ID.
   - Merge into the current view model.

5. Add UI states.
   - Loading skeleton.
   - Real data loaded.
   - Service unavailable.
   - Empty plan/benefits.
   - Demo fallback.

6. Add tests.
   - Real member summary success.
   - Benefits success.
   - Missing member.
   - Service unavailable.

## Suggested Files

- `apps/web/src/components/PlanDetailsView.tsx`
- `apps/web/src/lib/api/eligibility.ts`
- `apps/web/src/app/dashboard/plan/page.tsx`
- Plan page tests

## Validation

- `pnpm --filter web typecheck`
- `pnpm --filter web build`
- Page-level test for real API success and failure

## Risks

- Backend response names may not match current mock view model.
- Some benefit fields may be sparse.
- Demo member fallback can accidentally remain hidden if not labeled.

## Done When

- The Plan page can show real member and benefits data.
- Users can tell when data is real, demo, or unavailable.

