# Component 07 - Prometheus + Grafana Self-Hosted - Implementation Plan

> Step-by-step. Check off as you go.

1. [ ] Author `infra/prometheus/prometheus.yml` with 15s scrape interval and all 6 service targets.
2. [ ] Author `infra/grafana/datasources.yml` with Prometheus as the default datasource.
3. [ ] Hand-author 4 dashboards JSON (start from Grafana UI, export, commit to `infra/grafana/dashboards/`).
4. [ ] Add prometheus and grafana services to `docker-compose.yml`.
5. [ ] Map ports: prometheus on 9090, grafana on 3002 (avoid Langfuse's 3001).
6. [ ] Mount dashboards via Grafana provisioning.
7. [ ] Bring everything up.
8. [ ] Confirm Grafana shows all 4 dashboards on startup.
9. [ ] Commit with message `chore(infra): prometheus and grafana self-hosted with provisioned dashboards`.

