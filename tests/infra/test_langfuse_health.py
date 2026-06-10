"""Component 05 - Langfuse self-hosted health endpoint."""
import os
import pytest
import httpx


@pytest.mark.integration
def test_langfuse_health():
    base = os.environ.get("LANGFUSE_HOST", "http://localhost:3001")
    r = httpx.get(f"{base}/api/public/health", timeout=5.0)
    assert r.status_code == 200
