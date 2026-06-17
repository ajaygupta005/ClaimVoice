"""Component 06 - a run logged via the SDK is queryable."""
import os
import pytest


@pytest.mark.integration
def test_log_and_query_run():
    mlflow = pytest.importorskip("mlflow")
    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    with mlflow.start_run() as run:
        mlflow.log_metric("smoke_metric", 0.42)
    fetched = mlflow.get_run(run.info.run_id)
    assert fetched.data.metrics["smoke_metric"] == 0.42
