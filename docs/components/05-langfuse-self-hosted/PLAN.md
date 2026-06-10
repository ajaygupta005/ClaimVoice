# Component 05 - Langfuse Self-Hosted (LLM Observability) - Implementation Plan

> Step-by-step. Check off as you go.

1. [ ] Author `infra/langfuse/docker-compose.fragment.yml` with the official `langfuse/langfuse:latest` image.
2. [ ] Wire `DATABASE_URL` env to our shared Postgres.
3. [ ] Map port 3001 to container's 3000.
4. [ ] Merge fragment into root `docker-compose.yml` as the `langfuse` service.
5. [ ] Update `.env.example` with `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST=http://localhost:3001`.
6. [ ] Author `infra/langfuse/README.md` documenting first-run UI setup (signup, project create, key capture).
7. [ ] Bring it up: `docker compose up langfuse`.
8. [ ] Open the UI, sign up admin, create project, copy keys into local `.env`.
9. [ ] Send a manual test trace via curl to confirm the connection.
10. [ ] Commit with message `chore(infra): langfuse self-hosted observability`.

