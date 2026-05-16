# ML Lifecycle

```
ml/models/<m>/train.py  →  MLflow (params + metrics)  →
Model Registry (Staging → Production)  →  artifacts/ via DVC  →
src/<svc>/inference/<m>_runner.py loads at service startup
```
