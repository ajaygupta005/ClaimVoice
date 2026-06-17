"""Component 08 - .pre-commit-config.yaml validates."""
import yaml
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def test_pre_commit_config_parses():
    p = ROOT / ".pre-commit-config.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert "repos" in data
    assert len(data["repos"]) >= 4


def test_secrets_baseline_present():
    p = ROOT / ".secrets.baseline"
    assert p.exists(), ".secrets.baseline missing"


def test_required_hooks_configured():
    p = ROOT / ".pre-commit-config.yaml"
    text = p.read_text(encoding="utf-8")
    for hook in ["ruff", "mypy", "prettier", "detect-secrets"]:
        assert hook in text, f"pre-commit config missing hook: {hook}"
