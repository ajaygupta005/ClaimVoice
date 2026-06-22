# ADR 0001: Monorepo with pnpm and uv workspaces

## Status

Accepted.

## Context

ClaimVoice is one product made of a Next.js frontend, two Node (Fastify)
services, four Python (FastAPI) services, several shared packages, a data
pipeline, and an eval suite. These pieces share types, prompts, logging, and
deploy together. We had to decide between one repository or many.

## Decision

Use a single **monorepo** with **pnpm workspaces** for the JS/TS packages and a
**uv workspace** for the Python services, orchestrated by **Turborepo** for
builds and **just** for task running.

## Reasons

- **Shared contracts in one place.** Types, prompts, logging, and observability
  are shared packages; a monorepo lets a change and its consumers move in one
  commit and one CI run.
- **Atomic cross-service changes.** A schema change in eligibility and the
  voice-agent tool that calls it land together — no cross-repo version dance.
- **One CI, one review surface.** Easier for a small team to keep everything
  green and reviewed.
- **pnpm + uv are workspace-native** and fast, so the monorepo stays cheap to
  install even with many packages.

## Consequences

- The repo layout has `apps/`, `services/`, `packages/`, `data/`, `eval/`,
  `infra/`, and `docs/` at the top level.
- CI installs the whole graph; Turbo caches per-package builds so this stays
  fast.
- Deploy configs are per-service (`railway.json`, `vercel.json`) even though the
  code lives together.

## Alternatives considered

- **Polyrepo (one repo per service)** — cleaner ownership boundaries, but cross
  -service changes need coordinated PRs and version bumps, which is overhead a
  small team does not want.
- **Single repo, no workspaces** — would lose dependency hoisting, shared-package
  resolution, and per-package caching.
