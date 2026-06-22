# Component 58 - WS-2 Shared API Client and Service Status Plan

## Implementation Steps

1. Inspect current WS-2 API usage.
   - Review `apps/web/src/app/api/*`.
   - Review `VoiceAssistantUI.tsx`.
   - Review card, plan, and provider pages.

2. Create shared client types.
   - Define common success/error response shapes.
   - Define service status and data-source labels.
   - Keep types small enough for UI components to use directly.

3. Create service client modules.
   - Voice Agent client.
   - Eligibility client.
   - Providers client.
   - Document AI client.

4. Route browser requests safely.
   - Use Next.js API routes where needed.
   - Keep API keys server-side.
   - Keep service base URLs configurable.

5. Add service status helpers.
   - Query health endpoints where available.
   - Normalize status into `real`, `demo`, or `unavailable`.
   - Make status renderable by existing dashboard badges.

6. Add tests.
   - Unit test response normalization.
   - Unit test network failure handling.
   - Unit test service unavailable handling.

## Suggested Files

- `apps/web/src/lib/api/client.ts`
- `apps/web/src/lib/api/types.ts`
- `apps/web/src/lib/api/voice-agent.ts`
- `apps/web/src/lib/api/eligibility.ts`
- `apps/web/src/lib/api/providers.ts`
- `apps/web/src/lib/api/document-ai.ts`
- `apps/web/src/app/api/*` as needed for safe proxy routes

## Validation

- `pnpm --filter web typecheck`
- `pnpm --filter web build`
- Targeted unit tests for the API client layer

## Risks

- Accidentally exposing service secrets to browser code.
- Creating too much abstraction before page wiring.
- Hiding backend failures behind demo fallback.

## Done When

- Future WS-2 pages can call real services through one consistent client layer.
- Real/demo/unavailable state is explicit.
- No dashboard page needs custom ad hoc fetch/error handling for these services.

