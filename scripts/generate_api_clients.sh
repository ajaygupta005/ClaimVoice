#!/usr/bin/env bash
set -euo pipefail
# Generate TypeScript clients from each FastAPI service's OpenAPI spec
SERVICES=(document-ai eligibility providers voice-agent)
for svc in "${SERVICES[@]}"; do
  echo "→ generating client for $svc"
  npx @hey-api/openapi-ts \
    --input "http://localhost:8000/openapi.json" \
    --output "packages/shared-types/src/api/$svc" \
    --client fetch
done
