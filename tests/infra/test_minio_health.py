"""Component 02 - MinIO health endpoint."""
import os
import pytest
import httpx

from ._helpers import skip_if_unreachable


@pytest.mark.integration
def test_minio_health_live():
    endpoint = os.environ.get("S3_ENDPOINT", "http://localhost:9000")
    skip_if_unreachable(f"{endpoint}/minio/health/live")
    r = httpx.get(f"{endpoint}/minio/health/live", timeout=5.0)
    assert r.status_code == 200
