"""Shape checks for the hallucination eval golden dataset."""
import json
from pathlib import Path

DATASET = Path(__file__).resolve().parent.parent / "datasets" / "hallucination_golden.json"

REQUIRED = {"plan_context", "question", "facts_available", "truth_label"}
VALID_LABELS = {"grounded", "hallucinated"}


def _load():
    return json.loads(DATASET.read_text(encoding="utf-8"))


def test_dataset_loads_and_has_cases():
    data = _load()
    assert isinstance(data, list)
    assert len(data) >= 10


def test_each_record_has_required_fields():
    for i, rec in enumerate(_load()):
        missing = REQUIRED - rec.keys()
        assert not missing, f"record {i} missing {missing}"


def test_facts_available_is_a_list():
    for rec in _load():
        assert isinstance(rec["facts_available"], list)


def test_truth_labels_are_valid():
    for rec in _load():
        assert rec["truth_label"] in VALID_LABELS, rec["truth_label"]
