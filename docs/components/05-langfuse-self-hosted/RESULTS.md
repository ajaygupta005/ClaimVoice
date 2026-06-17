# Component 05 - Langfuse - Results

## Checklist
- [ ] `docker compose up -d langfuse` brings the UI up at :3001
- [ ] Created project, copied keys into `.env`
- [ ] Manual curl trace shows up in the UI

## Files in this commit
- `infra/langfuse/README.md`
- `docker-compose.yml` (added langfuse service)
- `.env.example` (added LANGFUSE_* vars)

## Commit
```
git add docker-compose.yml .env.example infra/langfuse/ tests/infra/test_langfuse_health.py tests/infra/test_langfuse_can_create_trace.py docs/components/05-langfuse-self-hosted/
git commit -m "chore(infra): add langfuse self-hosted for llm observability"
```
