"""Component 01 - validate root pyproject.toml uv workspace."""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

EXPECTED_MEMBERS = {
    "services/document-ai",
    "services/eligibility",
    "services/providers",
    "services/voice-agent",
    "eval",
    "packages/shared-logging/python",
    "packages/shared-observability/python",
}


def test_uv_workspace_members_present():
    with open(ROOT / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    members = set(data.get("tool", {}).get("uv", {}).get("workspace", {}).get("members", []))
    missing = EXPECTED_MEMBERS - members
    assert not missing, f"uv workspace missing members: {missing}"
