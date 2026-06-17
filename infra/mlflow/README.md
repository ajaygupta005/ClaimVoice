# MLflow (self-hosted)

Experiment tracking and model registry. UI at http://localhost:5000.

Backend: shared Postgres. Artifacts: MinIO bucket `mlflow-artifacts`.

## Bucket setup

Run once after `docker compose up -d`:

```bash
docker compose exec -T minio sh -c '
  mc alias set local http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD
  mc mb -p local/mlflow-artifacts
'
```

Or just create it via the MinIO console at http://localhost:9001.

## Quick test

```python
import mlflow
mlflow.set_tracking_uri("http://localhost:5000")
with mlflow.start_run():
    mlflow.log_metric("hello", 0.42)
```
