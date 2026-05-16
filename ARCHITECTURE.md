# ClaimVoice — Architecture

(See `docs/architecture.md` for the full ASCII system diagram, data flow,
component responsibilities, and cross-cutting concerns.)

## Services

- **apps/web** — Next.js 15 frontend (TypeScript, Tailwind, shadcn/ui, Clerk)
- **services/api-gateway** — Fastify gateway (auth, rate-limit, audit log)
- **services/document-ai** — FastAPI, LayoutLMv3 card OCR + payor classifier
- **services/eligibility** — FastAPI, X12 stub + plan knowledge graph + SBC RAG
- **services/providers** — FastAPI, NPI + PostGIS + Care Compare + MRF
- **services/voice-agent** — FastAPI + LangGraph + Claude tool-use
- **services/telephony** — Fastify + Twilio Media Streams bridge

## Cross-cutting

- **packages/shared-types** — auto-generated TypeScript from OpenAPI
- **packages/shared-prompts** — versioned Claude prompts
- **packages/shared-logging** — JSON log schema (loguru + pino)
- **packages/shared-observability** — OpenTelemetry + Langfuse clients
