# ClaimVoice — WS-4 / WS-5 / WS-6 Development Roadmap

> Branch: `feat/ws456-grounded-agent` · one commit per milestone · SPEC files in this `Plan/` dir.
> Goal: turn WS-4 (Eligibility), WS-5 (Providers), WS-6 (Voice Agent) from a mock pipeline into a
> **working, tested, grounded voice agent**. Definition of done = relevant Inspect AI evals green
> with real code + unit/integration tests per service against the seeded dev DB.

## Status — ✅ M0–M14 COMPLETE

All milestones below are implemented, tested, and committed on `feat/ws456-grounded-agent`
(one commit each; `git log --oneline origin/main..HEAD`). Tests green: WS-4 = 40, WS-5 = 20,
WS-6 = 236, eval gate = 51. Live http e2e verified. **See `Plan/HANDOFF.md` for run modes,
test commands, the dev-DB setup, and known limitations / next steps.**

## Scope (locked)

- **In scope:** Build WS-4 + WS-5 FastAPI services fully; wire WS-6 (LangGraph tools, hallucination
  guard, STT/TTS) to them. Real Claude + Deepgram + Cartesia adapters, each **key-gated with a
  deterministic mock fallback**. Use the existing browser voice UI (`apps/web`) and telephony bridge
  (`services/telephony`) as-is.
- **Non-goals (future):** WS-4 SBC RAG (pgvector + Voyage); WS-5 production geo (PostGIS
  `geography` + `ST_DWithin`); WS-8 api-gateway routing; WS-2 Plan/Providers tabs off mock data;
  real Twilio phone-call E2E.

## Environment

- Dev DB = `claimvoice` database on **Sentinel's** Postgres (`localhost:5432`, `postgres:16-alpine`
  — **no PostGIS, no pgvector**), already seeded by WS-1 (`scripts/seed_dev.ps1`).
- Geo is computed **app-side with Haversine** (no PostGIS needed).
- All money is **integer cents (BIGINT)**; display via `services/eligibility/.../lib/money.py`.

## Milestones

| M | Commit | WS | Depends on |
|---|---|---|---|
| M0 | `docs(plan): add WS-4/5/6 SPEC files + roadmap` | — | — |
| M1 | `chore(deps,config): add anthropic to eligibility, http+key settings` | all | M0 |
| M2 | `feat(data): seed canonical demo member + plan (golden values)` | WS-1/4 | M1 |
| M3 | `feat(ws4): GET /coverage (structured benefit lookup)` | WS-4 | M2 |
| M4 | `feat(ws4): POST /cost/estimate (copay/deductible/OOP)` | WS-4 | M2 |
| M5 | `feat(ws4): GET /formulary/lookup + alternatives` | WS-4 | M2 |
| M6 | `feat(ws4): POST /fact_check (structured grounding)` | WS-4 | M1 |
| M7 | `test(ws4): live-DB integration + coverage_qa/hallucination evals` | WS-4 | M3–M6 |
| M8 | `feat(ws5): enrich providers + GET /providers/near` | WS-5 | M1 |
| M9 | `feat(ws5): POST /providers/bulk` | WS-5 | M8 |
| M10 | `feat(ws6): real typed tool clients → WS-4/WS-5 (mock fallback)` | WS-6 | M3–M6, M8 |
| M11 | `feat(ws6): real hallucination guard via /fact_check (mock fallback)` | WS-6 | M6, M10 |
| M12 | `feat(ws6): real Deepgram STT + Cartesia TTS + VAD (key-gated)` | WS-6 | M1 |
| M13 | `feat(ws6): conversation memory + member threading` | WS-6 | M10 |
| M14 | `test(eval): e2e agent pipeline + e2e voice eval (real, seeded DB)` | WS-6/8 | M10–M13 |

**Topological order:** M0 → M1 → M2 → [WS-4: M3→M4→M5→M6→M7] → [WS-5: M8→M9] → [WS-6: M10→M11→M12→M13] → M14.

```
M0 ─ M1 ─ M2 ─┬─ M3 ─ M4 ─ M5 ─ M6 ─ M7
              ├─ M8 ─ M9
              └─ (M3..M6, M8) ─ M10 ─ M11 ─ M13 ─┐
                              M1 ─ M12 ──────────┴─ M14
```

## Verification matrix

| Milestone | Unit | Integration (DB up) | Inspect eval | Manual |
|---|---|---|---|---|
| M2 | — | demo-seed SQL | — | row counts |
| M3–M6 | schema/logic unit | endpoint vs seeded DB | — | — |
| M7 | — | `pytest services/eligibility -m integration` | coverage_qa, hallucination | — |
| M8 | `test_provider_lookup.py` | `test_providers_near.py` | `provider_lookup_eval.py` | — |
| M9 | — | `test_providers_bulk.py` | — | — |
| M10 | `test_tool_clients.py` + existing graph/scorer | `test_tools_live.py` | — | — |
| M11 | `test_hallucination_guard.py` | vs live `/fact_check` | — | — |
| M12 | streaming tests (mock) | key-gated (skipped w/o keys) | — | — |
| M13 | `test_agent_respond.py` | multi-turn memory | — | browser turn |
| M14 | full fast gate | `pytest -m integration` | agent_pipeline, e2e_voice | — |

### Commands (repo root)
- Fast gate (no DB/keys): `uv run pytest -m "not integration and not e2e" -q`
- Per service: `uv run pytest services/{eligibility,providers,voice-agent} -q`
- Integration (DB up): `uv run pytest -m integration -q`
- Inspect: `inspect eval eval/tasks/<task>.py` (`--model claude-sonnet-4-6` for model-graded)

## Env / keys (all optional in dev — gate real adapters)

| Var | Used by | Default behavior if unset |
|---|---|---|
| `DATABASE_URL` | all services | `postgresql://claimvoice:changeme@localhost:5432/claimvoice` |
| `ANTHROPIC_API_KEY` | WS-4 fact_check (claude), WS-6 composer | mock fallback |
| `DEEPGRAM_API_KEY` | WS-6 STT | MockStreamingSTT |
| `CARTESIA_API_KEY` | WS-6 TTS | MockStreamingTTS |

Mode toggles: `VOICE_AGENT_ANSWER_MODE`, `TOOL_MODE`, `FACT_CHECK_MODE`, `STT_MODE`, `TTS_MODE`
(each `mock` by default).

## Risk register

1. **Golden/seed mismatch** — agent_pipeline golden values ($75/$30/$1,500) + `CVX-0042-MT` not in
   generic seed → **M2** seeds them; DB-backed tools default to that member.
2. **Empty provider enrichment** — quality/specialty/accepting-new NULL for all 500 providers →
   **M8** deterministic NUCC-crosswalk backfill (columns already exist; no migration).
3. **No PostGIS/pgvector** — Haversine app-side (copy `_haversine_km` verbatim); SBC RAG + `ST_DWithin` deferred.
4. **API-key gating** — real adapters no-op to mock when keys absent so the fast gate runs keyless.
5. **Mock-fallback discipline** — preserve deterministic strings on `mode=mock`/error or ~15 unit
   assertions regress (`$` in cost answer, "deductible"/"lisinopril"/"cardiolog", grounded flags, `ok==grounded`).
6. **Schema-migration ownership** — any new migration only in `services/eligibility/alembic/versions/`.

See `SPEC-WS4.md`, `SPEC-WS5.md`, `SPEC-WS6.md` for per-workstream detail and frozen contracts.
