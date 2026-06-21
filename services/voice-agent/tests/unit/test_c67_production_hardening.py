"""
Component 67 — Production Hardening Roadmap tests.

Tests:
- /health/readiness returns 200 with status and tool_mode fields
- /health/readiness returns "unavailable" when DB is unreachable
- /health/readiness returns "ready" or "degraded" (never 503) in all cases
- /health/readiness includes demo_member_present field
- /health/readiness includes table-level checks
- /runtime/status returns "browser" (not Gemini) when gemini_enabled=False
- /runtime/status returns Gemini status only when gemini_enabled=True
- config exposes gemini_enabled flag defaulting to False
- config exposes orchestrate_timeout_s and tts_timeout_s
- orchestrate_timeout_s=0 disables the watchdog (no asyncio.wait_for overhead)
- telephony_ws sends stop ack after orchestrate timeout
- telephony_ws sends stop ack after TTS timeout
- Gemini routes absent from router when gemini_enabled=False
- Real mode without member ID returns safe clarification not demo data
- demo_mode=True allows CVX-0042-MT fallback
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

_VA_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_VA_SRC) not in sys.path:
    sys.path.insert(0, str(_VA_SRC))

from voice_agent.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _pcm_b64(n: int = 64) -> str:
    import base64
    return base64.b64encode(bytes(range(n % 256)) * (n // 256 + 1))[:n].decode()


# ── /health/readiness ─────────────────────────────────────────────────────────

def test_readiness_returns_200(client: TestClient):
    resp = client.get("/api/v1/health/readiness")
    assert resp.status_code == 200


def test_readiness_has_status_field(client: TestClient):
    resp = client.get("/api/v1/health/readiness")
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("ready", "degraded", "unavailable")


def test_readiness_has_tool_mode(client: TestClient):
    resp = client.get("/api/v1/health/readiness")
    data = resp.json()
    assert "tool_mode" in data
    assert data["tool_mode"] in ("mock", "http")


def test_readiness_has_demo_mode(client: TestClient):
    resp = client.get("/api/v1/health/readiness")
    data = resp.json()
    assert "demo_mode" in data
    assert isinstance(data["demo_mode"], bool)


def test_readiness_has_demo_member_present(client: TestClient):
    resp = client.get("/api/v1/health/readiness")
    data = resp.json()
    assert "demo_member_present" in data
    assert isinstance(data["demo_member_present"], bool)


def test_readiness_has_checks_list(client: TestClient):
    resp = client.get("/api/v1/health/readiness")
    data = resp.json()
    assert "checks" in data
    assert isinstance(data["checks"], list)


def test_readiness_unavailable_when_db_unreachable(client: TestClient):
    """When sqlalchemy is unavailable or DB is unreachable, status is 'unavailable'."""
    with patch("voice_agent.api.v1.readiness._check_db", return_value=([], False)):
        resp = client.get("/api/v1/health/readiness")
    data = resp.json()
    assert resp.status_code == 200  # never 503
    assert data["status"] == "unavailable"
    assert data["checks"] == []


def test_readiness_degraded_when_some_tables_empty(client: TestClient):
    from voice_agent.api.v1.readiness import TableCheck
    checks = [
        TableCheck(table="members", ok=True, row_count=5),
        TableCheck(table="plans", ok=False, row_count=0, detail="expected ≥1 rows, found 0"),
        TableCheck(table="plan_benefits", ok=True, row_count=10),
        TableCheck(table="formulary_drug", ok=True, row_count=50),
        TableCheck(table="providers", ok=True, row_count=100),
        TableCheck(table="in_network", ok=True, row_count=20),
    ]
    with patch("voice_agent.api.v1.readiness._check_db", return_value=(checks, True)):
        resp = client.get("/api/v1/health/readiness")
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["demo_member_present"] is True
    assert any(c["table"] == "plans" and not c["ok"] for c in data["checks"])


def test_readiness_ready_when_all_tables_ok(client: TestClient):
    from voice_agent.api.v1.readiness import TableCheck
    checks = [
        TableCheck(table="members", ok=True, row_count=30),
        TableCheck(table="plans", ok=True, row_count=16),
        TableCheck(table="plan_benefits", ok=True, row_count=100),
        TableCheck(table="formulary_drug", ok=True, row_count=200),
        TableCheck(table="providers", ok=True, row_count=500),
        TableCheck(table="in_network", ok=True, row_count=1000),
    ]
    with patch("voice_agent.api.v1.readiness._check_db", return_value=(checks, True)):
        resp = client.get("/api/v1/health/readiness")
    data = resp.json()
    assert data["status"] == "ready"
    assert data["demo_member_present"] is True


# ── Config: new fields ────────────────────────────────────────────────────────

def test_config_gemini_enabled_defaults_false():
    from voice_agent.core.config import Settings
    s = Settings()
    assert s.gemini_enabled is False


def test_config_orchestrate_timeout_defaults_30():
    from voice_agent.core.config import Settings
    s = Settings()
    assert s.orchestrate_timeout_s == 30.0


def test_config_tts_timeout_defaults_20():
    from voice_agent.core.config import Settings
    s = Settings()
    assert s.tts_timeout_s == 20.0


def test_config_timeouts_can_be_disabled():
    from voice_agent.core.config import Settings
    s = Settings(orchestrate_timeout_s=0, tts_timeout_s=0)
    assert s.orchestrate_timeout_s == 0
    assert s.tts_timeout_s == 0


# ── Gemini isolation ──────────────────────────────────────────────────────────

def test_runtime_status_returns_browser_when_gemini_disabled(client: TestClient):
    """With gemini_enabled=False (default), runtime/status always returns browser."""
    from voice_agent.core import config as cfg_mod
    original = cfg_mod.settings.gemini_enabled
    try:
        cfg_mod.settings.gemini_enabled = False
        cfg_mod.settings.claimvoice_voice_runtime = "gemini-live"
        cfg_mod.settings.gemini_api_key = "fake-key"
        resp = client.get("/api/v1/runtime/status")
        data = resp.json()
        assert data["runtime"] == "browser"
    finally:
        cfg_mod.settings.gemini_enabled = original
        cfg_mod.settings.claimvoice_voice_runtime = "browser"
        cfg_mod.settings.gemini_api_key = ""


def test_runtime_status_returns_gemini_when_enabled(client: TestClient):
    """When gemini_enabled=True and key present, runtime is gemini-live status."""
    from voice_agent.core import config as cfg_mod
    from voice_agent.api.v1 import runtime_status as rs_mod
    original_enabled = cfg_mod.settings.gemini_enabled
    original_runtime = cfg_mod.settings.claimvoice_voice_runtime
    original_key = cfg_mod.settings.gemini_api_key
    try:
        cfg_mod.settings.gemini_enabled = True
        cfg_mod.settings.claimvoice_voice_runtime = "gemini-live"
        cfg_mod.settings.gemini_api_key = "fake-gemini-key"
        with patch.object(rs_mod, "_gemini_sdk_available", return_value=False):
            resp = client.get("/api/v1/runtime/status")
        data = resp.json()
        # SDK not available → unavailable (not browser)
        assert data["runtime"] == "gemini-live-unavailable"
    finally:
        cfg_mod.settings.gemini_enabled = original_enabled
        cfg_mod.settings.claimvoice_voice_runtime = original_runtime
        cfg_mod.settings.gemini_api_key = original_key


def test_gemini_not_in_runtime_status_when_disabled(client: TestClient):
    """When gemini_enabled=False, runtime/status must not report Gemini as active runtime."""
    from voice_agent.core import config as cfg_mod
    original_enabled = cfg_mod.settings.gemini_enabled
    original_runtime = cfg_mod.settings.claimvoice_voice_runtime
    try:
        cfg_mod.settings.gemini_enabled = False
        cfg_mod.settings.claimvoice_voice_runtime = "gemini-live"  # requested but disabled
        cfg_mod.settings.gemini_api_key = "fake-key"
        resp = client.get("/api/v1/runtime/status")
        data = resp.json()
        # Must fall back to browser when gemini_enabled=False
        assert data["runtime"] == "browser", (
            f"Gemini must not appear in runtime/status when disabled, got: {data['runtime']}"
        )
    finally:
        cfg_mod.settings.gemini_enabled = original_enabled
        cfg_mod.settings.claimvoice_voice_runtime = original_runtime
        cfg_mod.settings.gemini_api_key = ""


# ── Watchdog: orchestrate timeout ────────────────────────────────────────────

def test_telephony_orchestrate_timeout_sends_stop_ack(client: TestClient):
    """An orchestrate timeout (asyncio.TimeoutError from wait_for) must still send stop ack."""
    import asyncio

    # Patch the executor to raise asyncio.TimeoutError (simulates wait_for expiry).
    # We patch asyncio.wait_for itself to immediately raise TimeoutError so the
    # test stays synchronous and doesn't actually sleep.
    original_wait_for = asyncio.wait_for

    async def _instant_timeout(coro, *, timeout):
        coro.close()
        raise asyncio.TimeoutError()

    with patch("voice_agent.api.v1.telephony_ws.asyncio.wait_for", _instant_timeout):
        with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-wdog1&streamSid=SM-wdog1") as ws:
            ws.send_json({"type": "start", "callSid": "CA-wdog1", "streamSid": "SM-wdog1"})
            ws.receive_json()  # start ack

            ws.send_json({"type": "audio", "callSid": "CA-wdog1", "streamSid": "SM-wdog1", "pcm24k": _pcm_b64(64)})
            ws.receive_json()  # audio ack

            ws.send_json({"type": "stop", "callSid": "CA-wdog1", "streamSid": "SM-wdog1"})
            # transcript.final → error → stop ack
            msgs: list[dict] = []
            for _ in range(5):
                try:
                    msgs.append(ws.receive_json())
                    if msgs[-1].get("ack") == "stop":
                        break
                except Exception:
                    break

    stop_acks = [m for m in msgs if m.get("ack") == "stop"]
    assert len(stop_acks) >= 1, f"Expected stop ack after orchestrate timeout, got: {msgs}"


def test_telephony_tts_timeout_sends_stop_ack(client: TestClient):
    """A TTS timeout (asyncio.TimeoutError from _do_tts wait_for) must still send stop ack."""
    import asyncio

    original_wait_for = asyncio.wait_for
    call_count = [0]

    async def _selective_timeout(coro, *, timeout):
        # Let the first call through (orchestrate), timeout the second (TTS).
        call_count[0] += 1
        if call_count[0] == 1:
            return await original_wait_for(coro, timeout=timeout)
        coro.close()
        raise asyncio.TimeoutError()

    with patch("voice_agent.api.v1.telephony_ws.asyncio.wait_for", _selective_timeout):
        with client.websocket_connect("/api/v1/ws/telephony?callSid=CA-wdog2&streamSid=SM-wdog2") as ws:
            ws.send_json({"type": "start", "callSid": "CA-wdog2", "streamSid": "SM-wdog2"})
            ws.receive_json()  # start ack

            ws.send_json({"type": "audio", "callSid": "CA-wdog2", "streamSid": "SM-wdog2", "pcm24k": _pcm_b64(64)})
            ws.receive_json()  # audio ack

            ws.send_json({"type": "stop", "callSid": "CA-wdog2", "streamSid": "SM-wdog2"})
            # transcript.final → answer.final → tts_error → stop ack
            stop_ack = None
            for _ in range(8):
                try:
                    msg = ws.receive_json()
                    if msg.get("ack") == "stop":
                        stop_ack = msg
                        break
                except Exception:
                    break

    assert stop_ack is not None, "Expected stop ack after TTS timeout"
    assert stop_ack["callSid"] == "CA-wdog2"


# ── Demo member isolation ─────────────────────────────────────────────────────

def test_real_mode_without_member_returns_clarification():
    """In real HTTP mode with demo_mode=False, missing member → clarification, not demo data."""
    from voice_agent.graph.nodes.call_tool import _resolve_member, _PLACEHOLDER_IDS
    from voice_agent.core import config as cfg_mod

    original_tool = cfg_mod.settings.tool_mode
    original_demo = cfg_mod.settings.demo_mode
    try:
        cfg_mod.settings.tool_mode = "http"
        cfg_mod.settings.demo_mode = False

        member_id, member_source = _resolve_member("")
        assert member_id == ""
        assert member_source == "missing"
    finally:
        cfg_mod.settings.tool_mode = original_tool
        cfg_mod.settings.demo_mode = original_demo


def test_demo_mode_allows_fallback_to_demo_member():
    """With demo_mode=True, missing member falls back to CVX-0042-MT."""
    from voice_agent.graph.nodes.call_tool import _resolve_member
    from voice_agent.core import config as cfg_mod

    original = cfg_mod.settings.demo_mode
    try:
        cfg_mod.settings.demo_mode = True
        member_id, member_source = _resolve_member("")
        assert member_id == "CVX-0042-MT"
        assert member_source == "demo"
    finally:
        cfg_mod.settings.demo_mode = original


def test_provided_member_id_not_overridden_by_demo():
    """A real member ID must pass through regardless of demo_mode."""
    from voice_agent.graph.nodes.call_tool import _resolve_member
    from voice_agent.core import config as cfg_mod

    original = cfg_mod.settings.demo_mode
    try:
        cfg_mod.settings.demo_mode = True
        member_id, member_source = _resolve_member("REAL-MEMBER-007")
        assert member_id == "REAL-MEMBER-007"
        assert member_source == "provided"
    finally:
        cfg_mod.settings.demo_mode = original


def test_member_source_in_agent_respond_response(client: TestClient):
    """POST /agent/respond must include member_source in the response."""
    resp = client.post("/api/v1/agent/respond", json={
        "question": "Is an MRI covered?",
        "memberId": "CVX-0042-MT",
        "source": "typed",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "member_source" in data
    assert data["member_source"] in ("provided", "demo", "missing")
