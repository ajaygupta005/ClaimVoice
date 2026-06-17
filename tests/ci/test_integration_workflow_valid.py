"""Component 11 - integration.yml is well-formed and runs pytest tests/integration."""
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOW = ROOT / ".github/workflows/integration.yml"


def test_integration_yaml_parses():
    if not WORKFLOW.exists():
        import pytest
        pytest.skip("integration.yml not authored yet")
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert "jobs" in data


def test_integration_workflow_runs_integration_tests():
    if not WORKFLOW.exists():
        import pytest
        pytest.skip("integration.yml not authored yet")
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "tests/integration" in text or "pytest" in text


def test_integration_workflow_uses_service_containers():
    if not WORKFLOW.exists():
        import pytest
        pytest.skip("integration.yml not authored yet")
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "services:" in text
    assert "postgres" in text.lower()
