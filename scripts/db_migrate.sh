#!/usr/bin/env bash
set -euo pipefail
for svc in eligibility providers voice-agent; do
  echo "→ migrating $svc"
  cd services/$svc && uv run alembic upgrade head && cd ../..
done
