# Component 70 - WS-2 SBC Evidence Citations Plan

## Implementation Steps

1. Inspect current WS-2 voice response types.
   - Find where agent responses are parsed.
   - Find transcript bubble rendering.
   - Find status/evidence-capable panels.

2. Add evidence types to the web API layer.
   - Keep fields aligned with WS-7 metadata.
   - Do not expose Voyage or backend secrets to the browser.

3. Render answer evidence.
   - Add compact evidence UI for agent answers.
   - Support collapsed long chunks.
   - Clear evidence between turns.

4. Add unavailable/empty behavior.
   - No chunks: no citation list.
   - RAG attempted but unavailable: optional small status label.
   - Structured-only answer: no evidence panel unless structured citations are added later.

5. Add tests.
   - Response with chunks renders citations.
   - Response without chunks renders no citations.
   - Long text truncates safely.
   - Evidence clears on the next turn.

## Suggested Files

- `apps/web/src/lib/api/*`
- `apps/web/src/components/VoiceAssistantUI.tsx`
- `apps/web/src/components/*`

## Validation

- `pnpm --filter @claimvoice/web typecheck`
- Manual browser test at `/dashboard/voice`
- Responsive check on desktop and narrow viewport

## Risks

- Rendering raw chunk text can make the UI noisy.
- Evidence from a previous turn can leak into the next turn if state is not reset.
- Calling eligibility RAG directly from the browser would expose unnecessary backend details.

## Done When

- RAG-backed answers display real evidence.
- Non-RAG answers remain clean.
- Empty/unavailable RAG states are honest.
- UI layout remains stable.
