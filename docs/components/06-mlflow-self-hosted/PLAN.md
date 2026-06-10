# Component 06 - MLflow Self-Hosted (Experiment Tracking) - Implementation Plan

> Step-by-step. Check off as you go.

1. [ ] Pre-create the `mlflow-artifacts` MinIO bucket via a one-shot init container OR document a manual step.
2. [ ] Author `infra/mlflow/docker-compose.fragment.yml` with the official `ghcr.io/mlflow/mlflow:latest` image.
3. [ ] Set the command: `mlflow server --host 0.0.0.0 --backend-store-uri postgresql://...@postgres:5432/claimvoice --artifacts-destination s3://mlflow-artifacts/`.
4. [ ] Set `MLFLOW_S3_ENDPOINT_URL` and AWS-compatible creds (point at MinIO).
5. [ ] Merge fragment into root `docker-compose.yml`.
6. [ ] Update `.env.example` with `MLFLOW_TRACKING_URI=http://localhost:5000`.
7. [ ] Author `infra/mlflow/README.md`.
8. [ ] Bring it up: `docker compose up mlflow`.
9. [ ] Run hello-world `mlflow.log_metric` from a notebook to confirm.
10. [ ] Commit with message `chore(infra): mlflow tracking server self-hosted`.

