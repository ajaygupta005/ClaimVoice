# Component 69 - WS-2 Dashboard Live Data - Plan

1. Add catch-all proxies `app/api/eligibility/[...slug]/route.ts` (-> :8002 `/api/v1/...`)
   and `app/api/providers/[...slug]/route.ts` (-> :8003 `/api/v1/providers/...`), defaulting
   to `localhost:8002/8003`, mirroring the voice-agent proxy (GET + POST, 10s timeout).
2. `PlanDetailsView.tsx`: `useState(mock)` + `useEffect` fetch of `members/{id}/summary` and
   `cost/estimate`; map into member / plan / costSummary; add a "live" badge; mock fallback.
3. `ProviderSearchView.tsx`: `useState(mockProviders)` + `useEffect` fetch of
   `providers/near` (specialty / lat / lng); map `ProviderOut` -> the card shape; mock
   fallback; in-network default off (demo plan has sparse in_network links).
4. `app/page.tsx`: `redirect('/dashboard/voice')`.
5. `app/api/voice-agent/respond/route.ts`: AbortSignal timeout 10s -> 30s.
