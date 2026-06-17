# Component 07 - Prometheus + Grafana Self-Hosted - Research

> Alternatives considered, decisions made, references.

## Prometheus vs Datadog/New Relic at this stage
- Zero cost. Free OSS. Self-hostable.
- Datadog is great but billable per host.

## Provisioned dashboards as JSON
- Version-controlled.
- Reproducible across environments.
- The pattern used by every serious Grafana shop.

## Why 4 dashboards now even before metrics exist
- Less rework later (we know what we want to track).
- Empty panels are acceptable until services emit metrics.

## References
- Prometheus: https://prometheus.io/docs/
- Grafana provisioning: https://grafana.com/docs/grafana/latest/administration/provisioning/

