# Logging

We use a single JSON log schema across Python and Node services so we can
query everything together.

## Schema

```json
{
  "timestamp": "2026-06-11T14:32:00.123Z",
  "level": "INFO",
  "service": "document-ai",
  "correlation_id": "abc-123",
  "event": "card.extracted",
  "message": "Card extraction succeeded",
  "extra": {}
}
```

## Levels

`DEBUG`, `INFO`, `WARN`, `ERROR`, `AUDIT`. AUDIT is for coverage statements;
those are never dropped.

## Correlation IDs

Set at the API gateway from the `X-Correlation-ID` header. Downstream services
read it from the same header (or via OTel context once we have observability).

## PII

The following fields are auto-redacted: `member_id, dob, name, phone, address,
ssn, email`. If you log a dict, redaction is recursive.
