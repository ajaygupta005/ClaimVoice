# Component 69 - WS-2 Dashboard Live Data - Results

## Checklist
- [x] `app/api/{eligibility,providers}/[...slug]/route.ts` proxies.
- [x] Plan tab live (member summary + cost), "live" badge, mock fallback.
- [x] Providers tab live (`providers/near`), mock fallback.
- [x] `/` -> `/dashboard/voice` redirect.
- [x] respond proxy timeout 10s -> 30s.

## Verification (via :3000)
- `/dashboard/voice|plan|providers` -> 200; `/` -> 307 -> `/dashboard/voice`.
- Plan proxy -> Demo Member . ClaimVoice Demo PPO . Gold.
- Providers proxy (cardiologist) -> total=3 (after the path fix).
- Full browser voice path: the respond proxy returns grounded `composer=claude` answers for
  all three intents.
- `pnpm --filter web typecheck` passes.

## Commit
```
8bb43b4 feat(ws2): wire Plan + Providers tabs to live data via Next proxies
8fc22dd fix(ws2): providers proxy targets /api/v1/providers/* (was /api/v1/*)
4775574 feat(ws2): redirect / to /dashboard/voice (landing was a placeholder)
07ee0fb feat(ws2,ws5): seed cardiology providers + raise voice proxy timeout to 30s
```

## Notes
- Card + Calls tabs remain mock and are still in the nav (a "hide" change was reverted at
  the user's request). For a demo, steer to Voice / Plan / Providers.
