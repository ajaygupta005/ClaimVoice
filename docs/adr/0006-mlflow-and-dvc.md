# ADR 0006: MLflow for experiments, DVC for data and model versioning

## Status

Accepted.

## Context

The Document AI workstream trains several models (card OCR, payor classifier,
SBC parser). We need to track experiments (params, metrics, runs) and version
the large artifacts (datasets, checkpoints) that do not belong in Git. The
choice has to be free, self-hostable, and work the same in dev and CI.

## Decision

Use **MLflow** for experiment tracking and the model registry, and **DVC**
for versioning datasets and model checkpoints, with **MinIO** as the shared
remote for both.

## Reasons

- **MLflow** is OSS (Apache 2), self-hostable with no quotas, and integrates
  with every training framework we use. The model registry (Staging /
  Production stages) is enough for our promotion flow.
- **DVC** versions large files by content hash and pushes the bytes to any
  S3-compatible remote. We already run MinIO, so the remote is free.
- The two compose cleanly: MLflow logs the artifact path, DVC tracks the bytes.

## Consequences

- Training scripts call `mlflow.log_metric` / `log_artifact`; the artifact
  destination is `s3://mlflow-artifacts/` on MinIO.
- `dvc.yaml` defines the `data -> train -> evaluate` pipeline so `dvc repro`
  rebuilds anything stale.
- Reproducibility is a property of the repo: a checkpoint is always pinned to
  the data and code that produced it.

## Alternatives considered

- **Weights & Biases** — excellent UX but the free tier has run/project limits
  and is SaaS-only for the hosted experience.
- **ClearML** — more features, more operational surface than we need.
- **LakeFS / Git LFS** — heavier or Git-coupled; DVC on MinIO is simpler.
