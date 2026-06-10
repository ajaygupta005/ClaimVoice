"""Component 06 - MLflow Tracking server health."""
import os
import pytest
import httpx


@pytest.mark.integration
def test_mlflow_root_returns_200():
    base = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
    r = httpx.get(base, timeout=5.0)
    assert r.status_code in (200, 302)
