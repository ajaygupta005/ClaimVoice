# Component 01 - Monorepo Foundation

> **Branch**: `chore/repo-init`  |  **Day(s)**: 1  |  **Workstream**: WS-7/WS-8

## Goal & Scope

Turn the empty repo into a working monorepo skeleton that supports a Next.js frontend, four Python FastAPI services, two Node Fastify services, shared packages, and a Python eval suite, all under a single repo.

**Required tools (all free)**:
- pnpm 9 (Node workspace manager)
- Node 20
- Python 3.12
- uv (Python workspace manager)
- just (task runner)
- Turborepo (JS build graph)

**Workspace boundaries**:
- pnpm workspaces: `apps/*`, `services/api-gateway`, `services/telephony`, `packages/*`
- uv workspace: `services/document-ai`, `services/eligibility`, `services/providers`, `services/voice-agent`, `eval`, `packages/shared-*/python`

**Out of scope**: any service code (just the skeleton).

