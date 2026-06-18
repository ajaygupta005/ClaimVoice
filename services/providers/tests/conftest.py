"""Shared fixtures for the providers service; auto-skips integration tests without a DB."""

from __future__ import annotations

import os

import pytest


def _db_reachable() -> bool:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return False
    try:
        import psycopg

        with psycopg.connect(
            url.replace("postgresql+psycopg://", "postgresql://"), connect_timeout=3
        ):
            return True
    except Exception:
        return False


_DB_OK = _db_reachable()


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    if _DB_OK:
        return
    skip = pytest.mark.skip(reason="live database not reachable (set DATABASE_URL)")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from providers.main import app

    return TestClient(app)
