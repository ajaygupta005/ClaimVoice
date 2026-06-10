# Component 05 - Langfuse Self-Hosted (LLM Observability)

> **Branch**: `chore/langfuse-self-hosted`  |  **Day(s)**: 4  |  **Workstream**: WS-7/WS-8

## Goal & Scope

Self-hosted Langfuse for tracing every Anthropic Claude call across all services.

**Endpoint**: Langfuse UI at `http://localhost:3001`.

**Backend store**: shared Postgres (`DATABASE_URL`).

**Project setup**:
- Manual flow to open the UI, sign up the local admin user, create a "ClaimVoice" project, capture public + secret keys.
- Keys written to `.env` as `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`.

**Out of scope**: client SDK wiring across services (that is component 9: shared-observability).

