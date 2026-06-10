"""Component 12 - ARCHITECTURE.md exists and contains a Mermaid block."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def test_architecture_md_exists():
    p = ROOT / "ARCHITECTURE.md"
    assert p.exists(), "ARCHITECTURE.md missing at repo root"


def test_architecture_has_mermaid_block():
    p = ROOT / "ARCHITECTURE.md"
    if not p.exists():
        import pytest
        pytest.skip("ARCHITECTURE.md not authored yet")
    text = p.read_text(encoding="utf-8")
    assert "```mermaid" in text or "flowchart" in text, "ARCHITECTURE.md missing Mermaid diagram"


def test_architecture_links_to_adrs():
    p = ROOT / "ARCHITECTURE.md"
    if not p.exists():
        import pytest
        pytest.skip("ARCHITECTURE.md not authored yet")
    text = p.read_text(encoding="utf-8")
    assert "adr" in text.lower(), "ARCHITECTURE.md should link to ADRs"
