# Component 19 - WS-2 Plan Details View

> **Branch**: `feat/ws2-plan-details-view` | **Day(s)**: 19 | **Workstream**: WS-2 / WS-4 integration surface

## Goal

Replace the Plan tab placeholder with a readable plan details screen.

This is a frontend-only component. Real eligibility lookup is not required yet. Use mock/demo data, but base it on existing repo artifacts instead of random values.

## Source Data

Use these repo files as reference:

- `eval/datasets/golden_qa.json`
- `docs/PROJECT_DEEPDIVE.md`
- `data/SPEC.md`

## Scope

Build the Plan tab at:

- `/dashboard/plan`

The screen should show:

- Member and plan summary
- Deductible / out-of-pocket summary
- Common coverage highlights
- Prior authorization notes
- Example questions the plan can answer

## Out of Scope

- Real X12 eligibility.
- Real plan graph API.
- Real SBC RAG.
- Backend changes.
- Editing or saving plan data.

## Acceptance Criteria

- Plan tab no longer shows a placeholder.
- Plan data is readable and demo-friendly.
- Mock values are based on existing repo examples where possible.
- UI matches the existing dashboard shell.
- No backend service is required.