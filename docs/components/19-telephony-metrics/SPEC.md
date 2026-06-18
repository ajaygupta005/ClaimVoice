# Component 19 - Telephony Metrics + Hardening

> Branch: `feat/telephony-metrics` | Day(s): 27 | Workstream: WS-7

Prometheus metrics for the telephony service exposed at `/metrics`, wired into the media-stream handler and recording upload. Idempotent call finalization so an abrupt socket close still counts the call and decrements the active gauge (stream-stop hardening).
