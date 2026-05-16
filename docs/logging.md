# Logging Contract

## Schema
JSON output with: timestamp, level, service, correlation_id, span_id,
user_id (hashed), event, message, extra.

## Correlation IDs
Generated at api-gateway, propagated via X-Correlation-ID header.

## Levels
DEBUG, INFO, WARN, ERROR, AUDIT (AUDIT is never sampled).

## PII safety
Middleware strips known PII fields before emission.
