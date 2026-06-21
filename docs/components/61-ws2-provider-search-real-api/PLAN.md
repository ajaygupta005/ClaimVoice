# Component 61 - WS-2 Provider Search from Providers APIs Plan

## Implementation Steps

1. Review current provider search UI.
   - Identify current mock fields and filters.
   - Map them to Providers API query parameters.

2. Add Providers client methods.
   - `searchProviders`
   - `getProviderByNpi`
   - `findProvidersNear`
   - `bulkProviders` if needed for details.

3. Wire search form.
   - Specialty.
   - State/location.
   - Distance if coordinates are available.
   - Accepting-new-patients filter when supported.

4. Normalize provider results.
   - Convert backend rows into UI card view models.
   - Preserve raw NPI and network fields.

5. Add UI states.
   - Loading.
   - Results.
   - Empty.
   - Error.
   - Demo fallback.

6. Add tests.
   - Successful result render.
   - Empty result.
   - API failure.
   - Filter mapping.

## Suggested Files

- `apps/web/src/components/ProviderSearchView.tsx`
- `apps/web/src/lib/api/providers.ts`
- `apps/web/src/app/dashboard/providers/page.tsx`
- Provider page tests

## Validation

- `pnpm --filter web typecheck`
- `pnpm --filter web build`
- Page-level provider search test

## Risks

- Provider location data may be incomplete.
- Search API semantics may differ from UI filter expectations.
- UI and voice-agent provider results can diverge if they normalize differently.

## Done When

- Provider search uses real Providers API data.
- The page no longer silently relies on mock results in normal mode.

