# ClaimVoice

A multi-modal AI agent for US health insurance members. Photograph your insurance card, then talk to an agent that knows your plan and nearby in-network providers.

This is the project repo. Full plan in `docs/PROJECT_SPEC.md` and day-by-day commits in `CLAIMVOICE_COMMIT_PLAN.xlsx`.

## Quickstart

```
just install
just up
just dev
```

You'll need pnpm, uv, just, and Docker installed first.

## Repo layout

- `apps/web` — Next.js frontend
- `services/` — backend services (document-ai, eligibility, providers, voice-agent, telephony, api-gateway)
- `packages/` — shared TypeScript and Python packages
- `data/` — ingestion scripts for CMS public data
- `eval/` — Inspect AI eval suite
- `infra/` — Docker compose pieces and dashboards
- `docs/` — spec, deep-dive, ADRs, and per-commit work units under `docs/components/`
