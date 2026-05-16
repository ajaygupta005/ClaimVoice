# ClaimVoice — Final Project Specification

**Version 1.0 · Locked plan, ready for execution**

> This document is the single source of truth for the 30-day ClaimVoice build.
> Everything in `CLAIMVOICE_COMMIT_PLAN.xlsx` traces back to a section here.
> If the plan and the spec ever disagree, the spec wins — update the plan to match.

---

## 1 · Problem Statement

### 1.1 Crisp version (elevator pitch)
US health-insurance members cannot get a simple answer — *"Is my MRI covered? How much will it cost? Where do I go?"* — without a 40-minute hold on a member-services line. ClaimVoice lets them photograph their insurance card and have a real voice conversation, by phone or in the browser, with an AI agent that has full context of their plan plus nearby in-network providers. Every coverage statement the agent makes is grounded in structured data, so Claude *narrates* the answer, never *invents* it.

### 1.2 Detailed framing
The US has 332 million insured members. Health payors collectively spend roughly **$20 billion per year on member-service call centres** with average hold times around 18 minutes, calls running 8–12 minutes, and member NPS below 20 — among the worst of any consumer industry. The pain persists because plan information lives in three disconnected silos: the payor's eligibility system, a 60-page employer-specific Summary-of-Benefits PDF, and an often-stale provider directory.

ClaimVoice unifies the three silos behind one multi-modal agent:
1. The member uploads or photographs their insurance card.
2. A layout-aware Document AI pipeline extracts plan fields with confidence scores.
3. A RAG layer retrieves benefit details from the Summary-of-Benefits PDF.
4. An X12 270/271 eligibility lookup confirms member status (stubbed for the project).
5. A LangGraph agent orchestrates tool calls (`check_coverage`, `estimate_cost`, `find_provider`, `check_formulary`).
6. A **hallucination guard** verifies every coverage or cost statement against the structured data before the LLM is allowed to speak it.

### 1.3 Why this satisfies the technical breadth requirement
The project deliberately exercises every AI/ML category in one cohesive flow:

| Category | Where it shows up |
| --- | --- |
| Computer Vision / Document AI | LayoutLMv3 card OCR, payor logo classifier, SBC parser |
| Classical ML / DS | Cost calculator, in-network filter, provider geo-ranking |
| GenAI (LLM) | Claude 3.5 Sonnet powering reasoning and narration |
| RAG | Voyage AI embeddings + pgvector over SBC PDFs and formulary |
| Agentic AI | LangGraph state machine with structured tool-use |
| Voice ML | Streaming Deepgram STT + Claude + Cartesia TTS |
| Data Engineering | Real public CMS datasets ingested via reproducible DVC pipelines |
| MLOps | MLflow experiment tracking, DVC versioning, Hydra configs, Inspect AI evals |

---

## 2 · Tech Stack (Claude-locked)

### 2.1 Component matrix

| Layer | Choice | Cost on a 30-day build |
| --- | --- | --- |
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui + TanStack Query | Free |
| API Gateway | Fastify on Node 20 | Free |
| Backend services | FastAPI on Python 3.12 + Pydantic v2 | Free |
| Auth | Clerk (10,000 MAU free tier) | Free |
| Primary DB | PostgreSQL 16 + **pgvector** + **PostGIS** | Free |
| Cache / sessions | Redis 7 | Free |
| Object storage | MinIO (also serves as DVC remote) | Free |
| Document AI (vision) | LayoutLMv3 + PaddleOCR fallback + ResNet-50 payor classifier | Free (open weights) |
| Structured output | **Instructor** library on top of Claude tool-use | Free |
| Primary LLM | **Anthropic Claude 3.5 Sonnet** via official SDK | ~$3 in / $15 out per 1M tokens |
| LLM gateway / fallback | LiteLLM | Free |
| Embeddings | **Voyage AI `voyage-3-large`** (50M tokens/month free) | Free for the project |
| Vector store | pgvector HNSW | Free |
| Agent orchestration | **LangGraph** (typed state machines) | Free |
| Voice STT | **Deepgram Nova-2** ($200 free credit on signup) | Free |
| Voice LLM | Claude 3.5 Sonnet streaming with tool-use | Already counted |
| Voice TTS | **Cartesia Sonic** (free tier ~10K chars/month) | Free for the project |
| Telephony | Twilio Media Streams ($15 trial; used mainly on demo day) | ~$5 |
| Experiment tracking | **MLflow** (self-hosted) | Free |
| Data + model versioning | **DVC** with MinIO remote | Free |
| ML config management | **Hydra** | Free |
| Eval harness | Inspect AI (UK AISI) + LangSmith free tier | Free |
| LLM observability | **Langfuse** (self-hosted) | Free |
| General observability | OpenTelemetry + Prometheus + Grafana | Free |
| CI/CD | GitHub Actions | Free |
| Frontend hosting (demo) | Vercel hobby tier | Free |
| Backend hosting (demo) | Railway / Render free tier | Free |

**Expected 30-day cash spend: $0–$30.**

### 2.2 The Claude-specific note on voice
Anthropic does not currently expose a native realtime API. For voice we orchestrate a streaming pipeline:

```
Mic / phone → Deepgram Nova-2 (streaming STT) →
              Claude 3.5 Sonnet (streaming with tool-use, hallucination guard) →
              Cartesia Sonic (streaming TTS) → Speaker
```

End-to-end p95 latency target is **< 900 ms**. The trade-off is buying Claude's stronger reasoning and tool-use for the zero-hallucination requirement of regulated healthcare.

---

## 3 · Public Data Sources (verified May 2026)

All data is **genuine, public, free, and current**. Stubs are documented honestly.

| Data | Source | Notes |
| --- | --- | --- |
| NPI provider registry | [CMS NPPES V2 Bulk Download](https://download.cms.gov/nppes/NPI_Files.html) | V2 format mandatory since Mar 2026. Latest dump May 11, 2026, 1.08 GB. Filter to NY metro ~50K rows. |
| NPI real-time lookup | [NPPES NPI Registry API](https://npiregistry.cms.hhs.gov/api-page) | Live, no auth. |
| Health plan + SBC data | [CMS Exchange Plan PUFs 2026](https://www.cms.gov/marketplace/resources/data/public-use-files) | 56.4 MB ZIP covering thousands of marketplace plans. |
| Marketplace API | [developer.cms.gov/marketplace-api](https://developer.cms.gov/marketplace-api/) | Powers HealthCare.gov. |
| Real SBC PDFs | HealthCare.gov plan listings | 5–10 PDFs for the RAG demo corpus. |
| In-network rates (MRF) | Aetna / BCBS public MRFs under the Transparency in Coverage rule | **Schema 2.0 mandatory** since Feb 2026. Use one payor's NYC subset for the demo. |
| Drug formulary | [CMS Part D Formulary Reference File CY 2026](https://www.cms.gov/medicare/coverage/prescription-drug-coverage/formulary-guidance) | April + December files available. |
| Quarterly Part D data | [data.cms.gov Quarterly Part D Plan Formulary file](https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers/quarterly-prescription-drug-plan-formulary-pharmacy-network-and-pricing-information) | Updated quarterly. |
| Provider quality | [CMS Care Compare API](https://data.cms.gov/provider-data/topics/hospitals/overall-hospital-quality-star-rating/) | Public, no auth. ~5,400 hospitals. |
| ICD-10 / HCPCS codes | CMS public downloads | Free. Use HCPCS only — CPT is paywalled by the AMA. |

### Stubbed for the project (documented in README)
- **X12 270/271 eligibility** — hand-crafted realistic responses keyed to test cards. Production would integrate via Availity or Change Healthcare.
- **Insurance card images** — 100 synthetic cards generated with Flux + Faker, no real PII.

---

## 4 · Architecture

```
                          ┌────────────────────────────────────────────────┐
                          │                USER / MEMBER                   │
                          │   (web browser  ·  mobile  ·  phone call)      │
                          └─────────┬───────────────────────┬──────────────┘
                                    │                       │
                            HTTPS REST + WS            PSTN voice call
                                    │                       │
                       ┌────────────▼───────────┐   ┌───────▼────────────┐
                       │  Next.js 15 Frontend   │   │  Twilio            │
                       │  (apps/web)            │   │  - PSTN gateway    │
                       │  • Card upload         │   │  - Media Streams   │
                       │  • Provider map        │   │    (μ-law 8kHz WS) │
                       │  • Voice chat UI       │   └────────┬───────────┘
                       │  • Clerk auth          │            │
                       └───────────┬────────────┘            │
                                   │                         │
                                   └────────────┬────────────┘
                                                │
                              ┌─────────────────▼─────────────────┐
                              │  API Gateway (Fastify)            │
                              │  services/api-gateway             │
                              │  • Clerk JWT · Rate limit         │
                              │  • Audit log · Correlation IDs    │
                              └──┬───────┬───────┬───────┬────────┘
                                 │       │       │       │
              ┌──────────────────┘       │       │       └──────────────────┐
              ▼                          ▼       ▼                          ▼
   ┌────────────────┐ ┌────────────────┐  ┌────────────────────┐ ┌────────────────────┐
   │ Document AI    │ │ Eligibility    │  │ Providers          │ │ Voice Agent        │
   │ (FastAPI)      │ │ (FastAPI)      │  │ (FastAPI)          │ │ (FastAPI+LangGraph)│
   │                │ │                │  │                    │ │                    │
   │ LayoutLMv3     │ │ X12 270/271    │  │ NPI registry       │ │ STT  → Deepgram    │
   │ Payor CNN      │ │  stub          │  │ PostGIS geo        │ │ LLM  → Claude 3.5  │
   │ Card OCR       │ │ Plan graph     │  │ Care Compare API   │ │ TTS  → Cartesia    │
   │ SBC parser     │ │ SBC RAG        │  │ MRF in-network     │ │ Tool-use loop      │
   │ Instructor+    │ │  (Voyage emb.) │  │ Specialty filter   │ │ Hallucination grd. │
   │  Claude        │ │ Drug formulary │  │                    │ │ Barge-in / VAD     │
   └────────┬───────┘ └────────┬───────┘  └────────┬───────────┘ └────────┬───────────┘
            │                  │                   │                       │
            │                  │                   │       (tool calls)    │
            └──────────────────┴───────────────────┴───────────────────────┘
                                          │
                          ┌───────────────▼───────────────────┐
                          │   Shared Data Layer               │
                          │   PostgreSQL 16 + pgvector +      │
                          │   PostGIS                         │
                          │   Redis 7  (sessions, cache)      │
                          │   MinIO    (cards, audio, DVC)    │
                          └───────────────┬───────────────────┘
                                          │
                          ┌───────────────▼───────────────────┐
                          │   Telephony Bridge                │
                          │   services/telephony (Node)       │
                          │   Twilio WS ↔ voice-agent         │
                          │   μ-law ↔ PCM16 + resample        │
                          └───────────────────────────────────┘

   EXTERNAL APIs
   Anthropic Claude · Voyage AI · Deepgram · Cartesia · Twilio · CMS NPPES · CMS Care Compare

   CROSS-CUTTING
   Langfuse (LLM traces) · OpenTelemetry · Prometheus + Grafana · MLflow (experiments)
   DVC (data + models) · Inspect AI (evals) · GitHub Actions (CI/CD)
```

---

## 5 · The 8 Workstreams

We use a **multi-contributor model** — every workstream has 3–5 active contributors, and every team member touches 4–5 workstreams across the 30 days. There are no rigid owners.

| # | Workstream | Includes |
| --- | --- | --- |
| **WS-1** | **Data Engineering & Acquisition** | NPPES V2 ingest → PostGIS; Health Insurance Exchange 2026 PUFs ETL; SBC PDF download + catalog; Aetna MRF Schema 2.0 parser; CMS Part D formulary ingest; ICD-10 / HCPCS lookup tables; synthetic 100-card generator (Flux + Faker); hand-crafted X12 271 stub responses; `data/README.md` documenting every source; reproducible DVC pipelines. |
| **WS-2** | **Frontend & UX (Next.js)** | App Router scaffolding; Clerk auth screens; 5-tab dashboard (Card / Plan / Providers / Voice / Calls); card-upload with SSE extraction status; Leaflet+OSM provider map with distance + in-network filter; voice chat UI with waveform + tool-call visibility; theme toggle; a11y; auto-generated API clients via `@hey-api/openapi-ts`. |
| **WS-3** | **Document AI** | ResNet-50 payor logo classifier; LayoutLMv3 region detection (member ID, plan, dates, RX); Instructor + Claude for ambiguous-field decoding; PaddleOCR fallback; SBC PDF parser with table extraction; confidence scoring + "ask user to confirm" UX; per-payor performance evaluation; bias / fairness eval (per-payor subgroup F1); model cards. |
| **WS-4** | **Eligibility & Plan Knowledge** | X12 270/271 stub service; plan knowledge graph in Postgres `(member)→(plan)→(tier)→(service)→(coverage)`; RAG over SBC PDFs via Voyage `voyage-3-large` + pgvector HNSW; drug-formulary lookup endpoint; cost estimator combining deductible state + in/out-network + copay rules; ICD-10 / HCPCS code search. |
| **WS-5** | **Provider Directory & Geo** | NPPES V2 → PostGIS provider table (~50K NYC providers); distance + specialty + accepting-new-patients filters; MRF in-network join; CMS Care Compare API integration for quality ratings; `find_provider` tool implementation; geocoding utilities; map API for frontend. |
| **WS-6** | **Voice Agent (LangGraph + Tools)** | LangGraph state machine (greet → identify → answer → confirm → close); tool definitions (`check_coverage`, `estimate_cost`, `find_provider`, `check_formulary`, `escalate_to_human`, `schedule_callback`); streaming orchestration Deepgram → Claude → Cartesia; **hallucination guard** (every coverage statement fact-checked against structured data before TTS); conversation memory; member identity verification; barge-in via VAD. |
| **WS-7** | **Telephony & Realtime Audio** | Twilio Media Streams WebSocket bridge; μ-law (8kHz) ↔ PCM16 (24kHz) codec + resampling; call recording with state-aware consent prompt (one-party vs. two-party); encrypted recording storage; inbound + outbound call flows; TwiML generation; webhook handlers. |
| **WS-8** | **DevOps, Eval, Compliance, Demo** | Docker compose for entire stack (Postgres + Redis + MinIO + Langfuse + MLflow + Prometheus + Grafana); GitHub Actions CI (lint + typecheck + tests + integration); Inspect AI eval suite (card OCR accuracy, coverage QA accuracy, hallucination detection, provider lookup); Langfuse trace integration across all Claude calls; OpenTelemetry instrumentation; structured logging contract; HIPAA-design documentation; ADRs; demo script; deployment to Vercel + Railway. |

---

## 6 · Project Structure

Single GitHub monorepo, pnpm + uv workspaces, production-standard with full ML/DS support. See `ARCHITECTURE.md` for the full tree and per-service layout.

### 6.1 Cross-cutting contracts

- **Logging** (`packages/shared-logging/`): JSON output with `timestamp, level, service, correlation_id, span_id, user_id (hashed), event, message, extra`. Correlation ID generated at API gateway, propagated via `X-Correlation-ID`. PII middleware strips known fields. Python uses loguru; Node uses pino; both emit the same shape.
- **Observability** (`packages/shared-observability/`): OpenTelemetry SDKs sending traces to Langfuse (LLM-specific) and a generic OTel collector. Prometheus `/metrics` per service. Grafana dashboards version-controlled in `infra/grafana/dashboards/`.
- **ML lifecycle** (`docs/ml-lifecycle.md`): `ml/models/<m>/train.py → MLflow logs → Model Registry (Staging → Production) → artifacts/ via DVC → src/<svc>/inference/<m>_runner.py loads at service startup`.
- **API contracts**: each FastAPI service auto-publishes OpenAPI; `scripts/generate_api_clients.sh` regenerates `packages/shared-types/` and `apps/web/src/lib/api-client/` for type-safety across the language boundary.

---

## 7 · 30-Day Plan (Option A — phase-weighted)

| Phase | Days | Focus | Commits |
| --- | --- | --- | --- |
| **Phase 1 — Foundation** | 1–5 | Monorepo scaffold; Docker compose; Postgres + Redis + MinIO + Langfuse + MLflow; Clerk auth; data ingestion scripts; base schemas; CI skeleton. | ~22 |
| **Phase 2 — Core ML & Services** | 6–14 | Card OCR (LayoutLMv3 + payor classifier) trained and serving; SBC RAG with Voyage + pgvector; NPI → PostGIS loaded; X12 stub; eligibility + provider services; basic text-only agent loop working end-to-end. | ~46 |
| **Phase 3 — Voice Integration** | 15–22 | Deepgram STT streaming; Claude tool-use in LangGraph; Cartesia TTS streaming; hallucination guard; Twilio Media Streams bridge; browser voice chat working end-to-end. | ~39 |
| **Phase 4 — Polish & Eval** | 23–27 | Inspect AI suite green; Langfuse + Prometheus dashboards; UI polish; error handling; integration bug-bash; refactor passes; one revert. | ~24 |
| **Phase 5 — Demo Prep** | 28–30 | Demo script, screen recording, slide deck, README finalisation, architecture diagrams, deployment to Vercel + Railway, dry runs. | ~19 |
| **TOTAL** | | | **150** |

---

## 8 · The 150-Commit Plan (`CLAIMVOICE_COMMIT_PLAN.xlsx`)

The spreadsheet is the operational daily plan. Each row represents one commit and contains:

| Column | Purpose |
| --- | --- |
| Day | 1–30 |
| Day_of_week | Mon–Sun (explains weekend lulls) |
| Time_slot | morning / afternoon / evening / late-night (person personality) |
| Person | Person 1–7 (dropdown) |
| Workstream | WS-1 … WS-8 (dropdown, color-coded) |
| Status | Triaging / Implementing / In Review / Merged / Reverted (dropdown) |
| Commit_type | feat / fix / refactor / chore / docs / test / style / perf / revert (dropdown) |
| Branch_name | e.g. `feat/voice-agent-tools` |
| Commit_message | Conventional Commits |
| **Plan_Detail** | **Detailed task description — what to actually build, libraries, files, approach** |
| **Acceptance_Criteria** | **How to verify the task is done** |
| Files_Touched | actual paths |
| Builds_On | reference to earlier branch (refactor / fix chains) |
| PR_Number | e.g. `#42` |
| Reviewer | Person 1–7 or `—` (dropdown) |
| Tests_Added | count |
| Done_Notes | freeform retrospective notes |

### 8.1 How to use the spreadsheet
1. Read it top-to-bottom each morning. The row's `Plan_Detail` is your task brief for the day.
2. As you start work, change `Status` from **Triaging** → **Implementing** (dropdown).
3. Open a PR matching the `Branch_name` and `Commit_message`. Status → **In Review**.
4. After merge, change Status → **Merged** and fill in `Done_Notes` with anything that diverged from the plan.
5. If reverted, change Status → **Reverted** and add the rationale in Notes.

### 8.2 Distribution (actuals)

**Per person** — slightly uneven by design (real teams aren't perfectly even):
| Person | Commits | Primary WS | Personality |
| --- | --- | --- | --- |
| Person 1 | 21 | WS-2 Frontend | morning/afternoon, weekday |
| Person 2 | 23 | WS-3 Document AI | afternoon/evening, weekend warrior |
| Person 3 | 22 | WS-4 Eligibility | evening/late-night, weekday |
| Person 4 | 17 | WS-5 Providers | morning/afternoon, weekday |
| Person 5 | 26 | WS-6 Voice Agent | afternoon/evening, weekend warrior |
| Person 6 | 18 | WS-7 Telephony | evening/late-night, weekend warrior |
| Person 7 | 23 | WS-8 DevOps | morning, weekday |

**Per workstream**: WS-1=10 · WS-2=21 · WS-3=20 · WS-4=19 · WS-5=13 · WS-6=25 · WS-7=14 · WS-8=28 = 150.

**Per phase**: P1=22 · P2=46 · P3=39 · P4=24 · P5=19 = 150.

### 8.3 Realism baked in
- **Cross-workstream contribution**: each person commits across 4–5 workstreams.
- **Refactor chains**: e.g. `#6 → #12 → #35` for NPI ingest; `#23 → #26 → #62 → #91 (revert)` for Document AI batching. The `Builds_On` column makes these visible.
- **Bug-fix loops**: bugs introduced and fixed by different people (closes `#11`, `#14`, `#21`, `#28`, `#34`, `#36`, `#43`, `#51`).
- **One revert** at commit `#91` on Day 19 — Person 2 rolls back their own earlier batching refactor that proved unnecessary at our scale.
- **PR review**: ~70% of commits go through PR with a reviewer different from the author; the other ~30% are direct-to-main for small fixes / docs.
- **Time-slot personality**: each person has a consistent rhythm (P3 late-night, P5 weekend-warrior, P7 morning-only).

---

## 9 · Locked Decisions Summary

| Decision | Value |
| --- | --- |
| Project name | ClaimVoice |
| Primary LLM | Anthropic Claude 3.5 Sonnet |
| Embeddings | Voyage AI `voyage-3-large` |
| Voice stack | Deepgram STT → Claude → Cartesia TTS |
| Telephony | Twilio Media Streams |
| Workstreams | 8 (incl. Data Engineering as WS-1) |
| Workstream ownership | None — distributed contribution |
| Team size | 7 people (Person 1 – Person 7) |
| Total days | 30 (Day 1 … Day 30, no real calendar dates) |
| Total commits | 150 |
| Commit distribution | Option A (phase-weighted) |
| Repository | Single GitHub monorepo (pnpm + uv workspaces) |
| ML stack | MLflow + DVC + Hydra + MinIO remote |
| Eval framework | Inspect AI |
| Observability | OpenTelemetry + Langfuse + Prometheus + Grafana |
| Experiment tracking | MLflow (self-hosted) |
| Data versioning | DVC with MinIO remote |
| Config management | Hydra (ML) + pydantic-settings (runtime) |
| Excel columns | 17 (with `Plan_Detail` + `Acceptance_Criteria`; no Commit_hash, no Lines_added/removed) |
| Status states | Triaging / Implementing / In Review / Merged / Reverted |
| Commit message format | Conventional Commits |
| Expected cash cost | $0–$30 over 30 days |

---

## 10 · References

- **Architecture diagram & per-service layout**: `ARCHITECTURE.md`
- **Operational commit plan**: `CLAIMVOICE_COMMIT_PLAN.xlsx`
- **Deep-dive on the project's enterprise rationale**: `docs/PROJECT_DEEPDIVE.md`
- **Architecture Decision Records**: `docs/adr/`
- **Data source catalog**: `docs/data_sources.md`
- **Logging & observability contracts**: `docs/logging.md`, `docs/observability.md`
- **ML lifecycle**: `docs/ml-lifecycle.md`
- **Compliance (HIPAA-design)**: `docs/compliance.md`
- **Runbook**: `docs/runbook.md`
- **Demo script**: `docs/demo_script.md`
- **Prompt catalogue**: `docs/prompts.md`

---

*End of specification.*
