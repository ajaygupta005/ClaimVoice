# Component 22 - Deploy Config (Vercel + Railway) - Results

- [ ] Push to main no longer emails a failure when secrets are unset.
- [ ] Deploy runs only when secrets exist.

Commit:
```
git add .github/workflows/deploy.yml .github/workflows/security.yml apps/web/vercel.json services/telephony/railway.json services/api-gateway/railway.json docs/components/22-deploy-config/
git commit -m "chore(ci): guard deploy + security workflows; add deploy configs"
```
