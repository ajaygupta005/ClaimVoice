# Components

Each subfolder represents one logical commit unit in the WS-7 + WS-8 plan for Phase 1 and Phase 2 (Days 1-14).

| # | Component | Branch | Day(s) |
| --- | --- | --- | --- |
| 01 | Monorepo Foundation | `chore/repo-init` | 1 |
| 02 | Data Layer (Postgres+pgvector+PostGIS, Redis, MinIO) | `chore/data-layer` | 1-2 |
| 03 | GitHub Actions CI Pipeline | `chore/ci-workflow` | 3 |
| 04 | Shared Logging + Prompts Packages | `feat/shared-packages-foundation` | 4 |
| 05 | Langfuse Self-Hosted | `chore/langfuse-self-hosted` | 4 |
| 06 | MLflow Self-Hosted | `chore/mlflow-self-hosted` | 5 |
| 07 | Prometheus + Grafana | `chore/prom-grafana` | 6 |
| 08 | Pre-Commit Hooks | `chore/pre-commit` | 7 |
| 09 | Shared Observability (OTel + Langfuse) | `feat/shared-observability` | 8 + 13 |
| 10 | Inspect AI Eval Suite Scaffold | `feat/eval-scaffold` | 10 |
| 11 | Integration CI + ADR-0002 | `chore/integration-ci-and-adr` | 11-12 |
| 12 | Telephony Scaffold + ARCHITECTURE.md | `feat/telephony-scaffold-and-arch` | 14 |

## Workflow per component

For each component:
1. Read `SPEC.md` to understand the goal.
2. Read `RESEARCH.md` to see what was considered.
3. Follow `PLAN.md` step by step.
4. Run the relevant tests under `tests/`.
5. Fill in `RESULTS.md` as the work progresses.
6. Commit using the branch name and message in the SPEC.

All tools used are **free and open-source**. Total cash cost for these 12 components: **$0**.
