"""Component 71 — WS-2/WS-7 RAG Readiness Preflight tests (eligibility service).

All tests mock the database and settings; no live DB required.

Scenarios:
- key_missing: VOYAGE_API_KEY not configured
- table_missing (pgvector absent): pgvector extension row not found
- table_missing (table absent): pgvector ok but sbc_chunks table row absent
- empty: table exists, COUNT(*) == 0
- no_plan_links: rows exist but none join to plans
- ready: rows exist and join to plans
- db_error: session.execute raises an exception
- HTTP endpoint: GET /api/v1/rag/readiness returns 200 in all cases
"""

from __future__ import annotations

import sys
import os
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Ensure the service source is importable when run with PYTHONPATH=services/eligibility/src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))


def _make_settings(voyage_key: str = "voy_test_key"):
    """Return a minimal Settings-like object with voyage_api_key set."""
    s = MagicMock()
    s.voyage_api_key = voyage_key
    return s


def _session_factory(rows: list[Any]):
    """
    Build a context-manager-compatible mock DB session whose execute() calls
    return successive fetchone() values from `rows`.
    """
    session = MagicMock()
    execute_results = []
    for row in rows:
        result = MagicMock()
        result.fetchone.return_value = row
        execute_results.append(result)
    session.execute.side_effect = execute_results

    @contextmanager
    def _ctx():
        yield session

    return _ctx


# ── Key missing ───────────────────────────────────────────────────────────────

def test_key_missing():
    from eligibility.api.v1.rag_readiness import _check_rag_readiness
    with patch("eligibility.api.v1.rag_readiness.settings", _make_settings(voyage_key="")):
        result = _check_rag_readiness()
    assert result.ragStatus == "key_missing"
    assert result.voyageConfigured is False
    assert result.pgvectorAvailable is False
    assert "VOYAGE_API_KEY" in result.ragReason


def test_key_placeholder_treated_as_missing():
    from eligibility.api.v1.rag_readiness import _check_rag_readiness
    with patch("eligibility.api.v1.rag_readiness.settings", _make_settings(voyage_key="   ")):
        result = _check_rag_readiness()
    assert result.ragStatus == "key_missing"


# ── pgvector absent ───────────────────────────────────────────────────────────

def test_pgvector_absent():
    from eligibility.api.v1.rag_readiness import _check_rag_readiness
    # fetchone() for pgvector check returns None
    ctx = _session_factory([None])
    with (
        patch("eligibility.api.v1.rag_readiness.settings", _make_settings()),
        patch("eligibility.api.v1.rag_readiness.db_session", ctx),
    ):
        result = _check_rag_readiness()
    assert result.ragStatus == "table_missing"
    assert result.pgvectorAvailable is False
    assert result.voyageConfigured is True
    assert "pgvector" in result.ragReason


# ── sbc_chunks table absent ───────────────────────────────────────────────────

def test_table_absent():
    from eligibility.api.v1.rag_readiness import _check_rag_readiness
    # pgvector row found, table row not found
    ctx = _session_factory([(1,), None])
    with (
        patch("eligibility.api.v1.rag_readiness.settings", _make_settings()),
        patch("eligibility.api.v1.rag_readiness.db_session", ctx),
    ):
        result = _check_rag_readiness()
    assert result.ragStatus == "table_missing"
    assert result.pgvectorAvailable is True
    assert "sbc_chunks" in result.ragReason


# ── Empty table ───────────────────────────────────────────────────────────────

def test_table_empty():
    from eligibility.api.v1.rag_readiness import _check_rag_readiness
    # pgvector ok, table ok, COUNT(*) == 0
    ctx = _session_factory([(1,), (1,), (0,)])
    with (
        patch("eligibility.api.v1.rag_readiness.settings", _make_settings()),
        patch("eligibility.api.v1.rag_readiness.db_session", ctx),
    ):
        result = _check_rag_readiness()
    assert result.ragStatus == "empty"
    assert result.sbcChunksCount == 0
    assert result.pgvectorAvailable is True
    assert "empty" in result.ragReason or "no rows" in result.ragReason


# ── No plan links ─────────────────────────────────────────────────────────────

def test_no_plan_links():
    from eligibility.api.v1.rag_readiness import _check_rag_readiness
    # pgvector ok, table ok, COUNT=5, linked=0
    ctx = _session_factory([(1,), (1,), (5,), (0,)])
    with (
        patch("eligibility.api.v1.rag_readiness.settings", _make_settings()),
        patch("eligibility.api.v1.rag_readiness.db_session", ctx),
    ):
        result = _check_rag_readiness()
    assert result.ragStatus == "no_plan_links"
    assert result.sbcChunksCount == 5
    assert "none are linked" in result.ragReason


# ── Ready ─────────────────────────────────────────────────────────────────────

def test_ready():
    from eligibility.api.v1.rag_readiness import _check_rag_readiness
    # pgvector ok, table ok, COUNT=42, linked=30
    ctx = _session_factory([(1,), (1,), (42,), (30,)])
    with (
        patch("eligibility.api.v1.rag_readiness.settings", _make_settings()),
        patch("eligibility.api.v1.rag_readiness.db_session", ctx),
    ):
        result = _check_rag_readiness()
    assert result.ragStatus == "ready"
    assert result.sbcChunksCount == 42
    assert result.voyageConfigured is True
    assert result.pgvectorAvailable is True
    assert "30" in result.ragReason


# ── DB error ──────────────────────────────────────────────────────────────────

def test_db_error():
    from eligibility.api.v1.rag_readiness import _check_rag_readiness

    @contextmanager
    def _failing_ctx():
        session = MagicMock()
        session.execute.side_effect = RuntimeError("connection refused")
        yield session

    with (
        patch("eligibility.api.v1.rag_readiness.settings", _make_settings()),
        patch("eligibility.api.v1.rag_readiness.db_session", _failing_ctx),
    ):
        result = _check_rag_readiness()
    assert result.ragStatus == "db_error"
    assert "RuntimeError" in result.ragReason


# ── HTTP endpoint tests ───────────────────────────────────────────────────────

from fastapi.testclient import TestClient
from fastapi import FastAPI


def _make_app():
    from eligibility.api.v1.rag_readiness import router
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


def test_endpoint_always_returns_200_when_key_missing():
    with patch("eligibility.api.v1.rag_readiness.settings", _make_settings(voyage_key="")):
        client = TestClient(_make_app())
        resp = client.get("/api/v1/rag/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ragStatus"] == "key_missing"
    assert data["voyageConfigured"] is False


def test_endpoint_returns_ready_shape():
    ctx = _session_factory([(1,), (1,), (10,), (8,)])
    with (
        patch("eligibility.api.v1.rag_readiness.settings", _make_settings()),
        patch("eligibility.api.v1.rag_readiness.db_session", ctx),
    ):
        client = TestClient(_make_app())
        resp = client.get("/api/v1/rag/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ragStatus"] == "ready"
    assert data["sbcChunksCount"] == 10
    assert data["voyageConfigured"] is True
    assert data["pgvectorAvailable"] is True
    # No secret values
    serialized = str(data)
    assert "voyage" not in serialized.lower() or "voyageConfigured" in serialized  # only the bool field name allowed
    assert "api_key" not in serialized.lower()


def test_endpoint_response_contains_no_secrets():
    """Regression: response must never include raw key material."""
    ctx = _session_factory([(1,), (1,), (5,), (5,)])
    with (
        patch("eligibility.api.v1.rag_readiness.settings", _make_settings(voyage_key="secret_key_value")),
        patch("eligibility.api.v1.rag_readiness.db_session", ctx),
    ):
        client = TestClient(_make_app())
        resp = client.get("/api/v1/rag/readiness")
    body_text = resp.text
    assert "secret_key_value" not in body_text
    assert "VOYAGE_API_KEY" not in body_text
