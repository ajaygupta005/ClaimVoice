"""Shared helpers for infra integration tests."""
import httpx
import pytest


def skip_if_unreachable(url: str, timeout: float = 2.0) -> None:
    """Skip the test when the service at url is not running.

    Lets the Integration CI job stay green when optional services
    (MinIO, MLflow, Langfuse) are not started in the runner, instead of
    relying on continue-on-error.
    """
    try:
        httpx.get(url, timeout=timeout)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout):
        pytest.skip(f"service not reachable at {url}")
