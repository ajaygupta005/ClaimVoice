# Component 06 - MLflow Self-Hosted (Experiment Tracking)

> **Branch**: `chore/mlflow-self-hosted`  |  **Day(s)**: 5  |  **Workstream**: WS-7/WS-8

## Goal & Scope

Self-hosted MLflow Tracking Server for ML experiment tracking + model registry.

**Endpoint**: MLflow UI at `http://localhost:5000`.

**Backend store**: shared Postgres (runs, params, metrics).

**Artifact store**: MinIO bucket `mlflow-artifacts` (s3://mlflow-artifacts/).

**Env**: `MLFLOW_TRACKING_URI=http://localhost:5000`.

**Out of scope**: training code (Document AI workstream owns that).

