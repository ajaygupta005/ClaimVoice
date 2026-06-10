"""Component 05 - we can write a trace into self-hosted Langfuse via the SDK."""
import os
import pytest


@pytest.mark.integration
def test_create_trace_via_sdk():
    """Stub: requires LANGFUSE_* keys captured from the UI."""
    pytest.skip("implement after Langfuse UI setup is documented in component 5 RESULTS.md")
    # TODO:
    # from langfuse import Langfuse
    # client = Langfuse()
    # trace = client.trace(name="ci-smoke")
    # assert trace.id is not None
