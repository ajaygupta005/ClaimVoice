"""Strip PII fields before logging."""

PII_FIELDS = {"member_id", "dob", "name", "phone", "address", "ssn", "email"}


def redact_pii(payload: dict, fields: set[str] = PII_FIELDS) -> dict:
    """Return a copy of payload with sensitive fields masked."""
    out = {}
    for k, v in payload.items():
        if k in fields and v is not None:
            out[k] = "[REDACTED]"
        elif isinstance(v, dict):
            out[k] = redact_pii(v, fields)
        else:
            out[k] = v
    return out
