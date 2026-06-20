# Component 22 - Deploy Config (Vercel + Railway) - Plan

1. Guard `deploy.yml` Vercel + Railway steps behind secret-presence checks.
2. Make `security.yml` run on schedule/manual only with `continue-on-error`.
3. Add `vercel.json` and per-service `railway.json`.
