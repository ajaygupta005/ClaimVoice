"""Component 06 - an artifact uploaded to MLflow lands in MinIO."""
import os
import tempfile
import pytest


@pytest.mark.integration
def test_artifact_upload_via_sdk():
    mlflow = pytest.importorskip("mlflow")
    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("hello mlflow")
        tmp = f.name
    with mlflow.start_run() as run:
        mlflow.log_artifact(tmp)
    artifacts = mlflow.artifacts.list_artifacts(run.info.run_id)
    assert any(a.path.endswith(".txt") for a in artifacts)
