# shared-logging

Same JSON log schema for Python (loguru) and Node (pino).

Schema fields: `timestamp, level, service, correlation_id, event, message, extra`.

PII fields are redacted automatically: `member_id, dob, name, phone, address, ssn, email`.
