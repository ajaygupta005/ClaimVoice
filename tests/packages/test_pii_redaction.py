"""Component 04 - PII redaction strips sensitive fields."""
import pytest


SENSITIVE_FIELDS = ["member_id", "dob", "name", "phone", "address"]


def test_pii_fields_redacted():
    """Stub: instantiate the shared-logging PII redactor with a payload, assert sensitive fields are masked."""
    pytest.skip("implement when packages/shared-logging/python is built")
    # TODO:
    # from shared_logging import redact_pii
    # payload = {"member_id": "ABC123", "name": "Alex", "ok_field": "fine"}
    # out = redact_pii(payload)
    # for f in SENSITIVE_FIELDS:
    #     if f in payload:
    #         assert out[f] != payload[f]
    # assert out["ok_field"] == "fine"
