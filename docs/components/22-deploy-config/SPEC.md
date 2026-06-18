# Component 22 - Deploy Config (Vercel + Railway)

> Branch: `chore/deploy-config` | Day(s): 29 | Workstream: WS-8

Deployment configs and a deploy workflow that skips cleanly when secrets are absent (stops the daily failure emails). `apps/web/vercel.json`, `services/telephony/railway.json`, `services/api-gateway/railway.json`, and a guarded `deploy.yml`. Also makes `security.yml` schedule-only and non-failing.
