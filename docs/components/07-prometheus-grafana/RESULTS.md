# Component 07 - Prometheus + Grafana - Results

## Checklist
- [ ] Prometheus UI at :9090 loads
- [ ] `up{}` query in Prometheus returns the 6 service targets (most DOWN, fine)
- [ ] Grafana at :3002 loads
- [ ] All 4 dashboards visible on startup

## Files in this commit
- `docker-compose.yml` (added prometheus + grafana)
- `infra/prometheus/prometheus.yml`
- `infra/grafana/datasources.yml`
- `infra/grafana/dashboards/dashboards.yml`
- `infra/grafana/dashboards/{services,llm_cost,voice_latency,cache}.json`

## Commit
```
git add docker-compose.yml infra/prometheus/ infra/grafana/ tests/infra/test_prometheus_config_valid.py tests/infra/test_grafana_dashboards_valid.py tests/infra/test_prometheus_up_query.py docs/components/07-prometheus-grafana/
git commit -m "chore(infra): add prometheus and grafana for metrics"
```
