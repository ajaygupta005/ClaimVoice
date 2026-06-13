# Component 20 - WS-2 Provider Search View - Implementation Plan

### Inspect
1. [ ] Read `docs/PROJECT_DEEPDIVE.md` WS-5 provider section.
2. [ ] Read `services/providers/README.md`.
3. [ ] Read `apps/web/src/components/ProviderMap.tsx`.
4. [ ] Read `apps/web/src/app/dashboard/providers/page.tsx`.
5. [ ] Review Card and Plan tab styling.

### Mock data
6. [ ] Add mock provider data to `apps/web/src/lib/mock-data.ts`.
7. [ ] Include provider name, specialty, distance, network status, accepting-patients status, rating, address, phone, and note.
8. [ ] Use NYC/Manhattan-style demo locations if no real provider seed exists.

### UI
9. [ ] Replace Providers placeholder with a real provider search view.
10. [ ] Add search/filter header.
11. [ ] Add distance filter.
12. [ ] Add in-network toggle.
13. [ ] Add accepting-patients toggle.
14. [ ] Add provider result cards.
15. [ ] Add mock map/location panel.
16. [ ] Add selected provider details panel.

### Verify
17. [ ] Run `pnpm --filter @claimvoice/web typecheck`.
18. [ ] Open `/dashboard/providers`.
19. [ ] Confirm filters render.
20. [ ] Confirm provider cards render.
21. [ ] Confirm selecting a provider updates details.
22. [ ] Confirm no backend service is required.

### Commit
23. [ ] Stage only frontend provider-view files and this component docs.
24. [ ] Commit with: