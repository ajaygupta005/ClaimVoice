"""Component 07 - every committed Grafana dashboard JSON has required keys."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DASH_DIR = ROOT / "infra/grafana/dashboards"


def test_each_dashboard_has_required_keys():
    if not DASH_DIR.exists():
        import pytest
        pytest.skip("infra/grafana/dashboards not built yet")
    for p in DASH_DIR.glob("*.json"):
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "panels" in data, f"{p.name} missing panels"
        assert "schemaVersion" in data, f"{p.name} missing schemaVersion"


def test_expected_dashboards_committed():
    if not DASH_DIR.exists():
        import pytest
        pytest.skip("infra/grafana/dashboards not built yet")
    names = {p.stem for p in DASH_DIR.glob("*.json")}
    expected = {"services", "llm_cost", "voice_latency", "cache"}
    missing = expected - names
    assert not missing, f"missing dashboards: {missing}"
