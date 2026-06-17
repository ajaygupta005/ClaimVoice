# Component 06 - MLflow Self-Hosted (Experiment Tracking) - Research

> Alternatives considered, decisions made, references.

## MLflow vs W&B
- Weights & Biases has a free tier but with project/run limits and SaaS lock-in.
- MLflow is fully OSS, Apache 2, self-hostable, zero quota.
- MLflow Model Registry is good enough for our use case.

## MLflow vs ClearML
- MLflow has the larger ecosystem (every framework integrates).
- ClearML has more features but more complexity.

## Why Postgres backend over SQLite
- Concurrent writes (multiple training runs at once).
- Runs-table query speed under load.

## Why MinIO for artifacts
- Already in our stack.
- S3-compatible API means the integration code does not change between dev and prod.

## References
- MLflow Tracking: https://mlflow.org/docs/latest/tracking.html
- MLflow Model Registry: https://mlflow.org/docs/latest/model-registry.html

