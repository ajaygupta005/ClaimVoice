"""Component 01 - validate pnpm-workspace.yaml."""
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

EXPECTED_GLOBS = {"apps/*", "services/api-gateway", "services/telephony", "packages/*"}


def test_pnpm_workspace_globs_present():
    data = yaml.safe_load((ROOT / "pnpm-workspace.yaml").read_text(encoding="utf-8"))
    actual = set(data.get("packages", []))
    missing = EXPECTED_GLOBS - actual
    assert not missing, f"pnpm-workspace.yaml missing globs: {missing}"
