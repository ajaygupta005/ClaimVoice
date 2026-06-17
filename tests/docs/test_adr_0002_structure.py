"""Component 11 - ADR-0002 has the standard 5 sections."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ADR = ROOT / "docs/adr/0002-claude-over-gpt.md"


REQUIRED_SECTIONS = ["Status", "Context", "Decision", "Consequences", "Alternatives"]


def test_adr_has_all_sections():
    if not ADR.exists():
        import pytest
        pytest.skip("ADR-0002 not authored yet")
    text = ADR.read_text(encoding="utf-8")
    for sec in REQUIRED_SECTIONS:
        assert sec in text, f"ADR-0002 missing section: {sec}"
