"""Component 07 - Prometheus /api/v1/query?query=up returns valid response."""
import os
import pytest
import httpx

from ._helpers import skip_if_unreachable


@pytest.mark.integration
def test_prometheus_up_query():
    base = os.environ.get("PROM_URL", "http://localhost:9090")
    skip_if_unreachable(f"{base}/-/healthy")
    r = httpx.get(f"{base}/api/v1/query", params={"query": "up"}, timeout=5.0)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "data" in data and "result" in data["data"]
