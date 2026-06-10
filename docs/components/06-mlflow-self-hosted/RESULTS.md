# Component 06 - MLflow - Results

## Checklist
- [ ] `docker compose up -d mlflow` brings UI up at :5000
- [ ] Created `mlflow-artifacts` bucket in MinIO
- [ ] `mlflow.log_metric` hello-world works

## Files in this commit
- `infra/mlflow/README.md`
- `docker-compose.yml` (added mlflow service)
- `.env.example` (added MLFLOW_TRACKING_URI)

## Commit
```
git add docker-compose.yml .env.example infra/mlflow/ tests/infra/test_mlflow_health.py tests/infra/test_mlflow_run_persists.py tests/infra/test_mlflow_artifact_upload.py docs/components/06-mlflow-self-hosted/
git commit -m "chore(infra): add mlflow tracking server self-hosted"
```
