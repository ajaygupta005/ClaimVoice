"""Component 10 - every golden Q&A record has the expected fields."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATASET = ROOT / "eval/datasets/golden_qa.json"

REQUIRED_FIELDS = {"member_context", "question", "expected_answer"}


def test_each_record_has_required_fields():
    if not DATASET.exists():
        import pytest
        pytest.skip("golden_qa.json not authored yet")
    records = json.loads(DATASET.read_text(encoding="utf-8"))
    assert isinstance(records, list) and len(records) >= 20, "expected at least 20 golden pairs"
    for i, r in enumerate(records):
        missing = REQUIRED_FIELDS - r.keys()
        assert not missing, f"record {i} missing fields: {missing}"
