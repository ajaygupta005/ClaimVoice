# Component 07 - Prometheus + Grafana Self-Hosted

> **Branch**: `chore/prom-grafana`  |  **Day(s)**: 6  |  **Workstream**: WS-7/WS-8

## Goal & Scope

Self-hosted Prometheus for metrics scraping + Grafana for dashboards.

**Endpoints**:
- Prometheus at `http://localhost:9090`
- Grafana at `http://localhost:3002`

**Scrape targets** (all 6 services):
- `document-ai:8001`, `eligibility:8002`, `providers:8003`, `voice-agent:8004`, `telephony:8005`, `api-gateway:8080`

**Initial dashboards**:
1. Service latency (p50/p95/p99 by endpoint).
2. LLM cost (per day, per service).
3. Voice latency (STT/LLM/TTS/network breakdown).
4. Cache hit rates.

**Out of scope**: actual service metrics emission (that comes from each service's `/metrics` endpoint built in their workstreams).

