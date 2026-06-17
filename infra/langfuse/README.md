# Langfuse (self-hosted)

LLM observability. UI at http://localhost:3001.

## First time setup

1. `docker compose up -d langfuse`
2. Open http://localhost:3001 and sign up (creates the local admin).
3. Create a project called "ClaimVoice".
4. Copy the public and secret keys into your `.env`:
   ```
   LANGFUSE_PUBLIC_KEY=pk-...
   LANGFUSE_SECRET_KEY=sk-...
   ```
5. Generate strong values for `LANGFUSE_NEXTAUTH_SECRET` and `LANGFUSE_SALT`
   if you want to deploy this anywhere real.
