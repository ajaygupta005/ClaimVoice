"""Component 01 - workspace structure smoke test."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

REQUIRED = [
    "apps", "services", "packages", "data", "eval",
    "infra", "docs", "scripts", "tests",
    "pnpm-workspace.yaml", "pyproject.toml",
    "turbo.json", "Justfile", ".gitignore",
]


def test_required_paths_exist():
    for p in REQUIRED:
        assert (ROOT / p).exists(), f"missing: {p}"


def test_gitignore_has_common_patterns():
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pat in ["node_modules", "__pycache__", ".venv"]:
        assert pat in gi
