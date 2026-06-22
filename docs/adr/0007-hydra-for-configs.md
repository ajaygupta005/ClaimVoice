# ADR 0007: Hydra for ML and ingestion configs

## Status

Accepted.

## Context

The data ingestion scripts and the model training scripts each have many
parameters (filter states, batch sizes, learning rates, model names, paths).
These need to be overridable per run without editing code, reproducible, and
composable across environments.

## Decision

Use **Hydra** for the ML training configs and the data-ingestion configs.
Runtime service configuration (env vars) stays with **pydantic-settings** /
**zod** — Hydra is only for the experiment/pipeline side.

## Reasons

- **Override from the command line.** `python train.py training.lr=3e-5` or
  `python npi_ingest.py npi.geo_filter.states=[NY,PA]` without touching files.
- **Composition and sweeps.** Config groups compose cleanly, and `--multirun`
  sweeps a parameter grid for free.
- **Reproducible.** Hydra snapshots the fully-resolved config for each run, so
  a result is pinned to the exact parameters that produced it.
- It is the de-facto standard for ML config in the Python ecosystem.

## Consequences

- ML configs live in `services/document-ai/ml/configs/`; ingestion configs in
  `data/ingest/configs/`.
- Training entry points use the `@hydra.main` decorator.
- Service runtime config is deliberately *not* Hydra — env validation at boot
  via pydantic-settings (Python) and zod (Node) keeps the two concerns separate.

## Alternatives considered

- **argparse** — fine for a handful of flags, painful for nested config and
  sweeps.
- **Plain YAML + manual loading** — loses overrides, composition, and the
  resolved-config snapshot.
