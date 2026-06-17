"""Component 03 - .github/workflows/ci.yml is well-formed."""
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CI_YAML = ROOT / ".github/workflows/ci.yml"


def test_ci_yaml_loads():
    data = yaml.safe_load(CI_YAML.read_text(encoding="utf-8"))
    assert "jobs" in data
    assert "on" in data or True in data  # YAML may parse "on:" as True key


def test_ci_runs_lint_and_typecheck():
    text = CI_YAML.read_text(encoding="utf-8")
    assert "lint" in text.lower()
    assert "typecheck" in text.lower() or "mypy" in text.lower()


def test_codeowners_paths_exist():
    co = ROOT / ".github/CODEOWNERS"
    assert co.exists(), "CODEOWNERS missing"
    lines = co.read_text(encoding="utf-8").splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        path = line.split()[0].lstrip("/")
        # Most CODEOWNERS paths are folder globs - just check the root exists
        first_segment = path.split("/")[0]
        if first_segment and not first_segment.startswith("*"):
            assert (ROOT / first_segment).exists(), f"CODEOWNERS references missing path: {first_segment}"
