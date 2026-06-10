"""Component 02 - MinIO health endpoint."""
import os
import pytest
import httpx


@pytest.mark.integration
def test_minio_health_live():
    endpoint = os.environ.get("S3_ENDPOINT", "http://localhost:9000")
    r = httpx.get(f"{endpoint}/minio/health/live", timeout=5.0)
    assert r.status_code == 200
