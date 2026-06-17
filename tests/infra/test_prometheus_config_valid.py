"""Component 07 - prometheus.yml is parseable."""
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def test_prometheus_config_loads():
    p = ROOT / "infra/prometheus/prometheus.yml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert "scrape_configs" in data


def test_prometheus_targets_include_all_services():
    p = ROOT / "infra/prometheus/prometheus.yml"
    text = p.read_text(encoding="utf-8")
    for svc in ["document-ai", "eligibility", "providers", "voice-agent", "telephony", "api-gateway"]:
        assert svc in text, f"prometheus.yml missing target: {svc}"
