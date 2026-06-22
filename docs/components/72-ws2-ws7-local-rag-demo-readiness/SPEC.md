# Component 72 - WS-2/WS-7 Local RAG Demo Readiness

## Purpose

Document and validate the local demo workflow required for SBC RAG to work end to end.

The endpoint alone is not enough. Local demos need seeded plans, pgvector migration, `VOYAGE_API_KEY`, and indexed SBC chunks.

## Required Demo Contract

A local RAG demo is ready only when:

- Docker Postgres uses the pgvector-enabled image.
- Database migrations include `sbc_chunks`.
- Seed data creates at least one usable plan and member.
- SBC ingest creates chunks linked to that plan.
- `VOYAGE_API_KEY` is configured.
- `POST /api/v1/sbc/retrieve` returns at least one chunk for a known question.
- Browser voice answer can show or use the evidence.

## Required Documentation

The component should document:

- Commands to seed local DB.
- Commands to run SBC ingest.
- How to find or verify a seeded plan UUID.
- Smoke-test curl for RAG retrieval.
- Browser UI test for answer plus citations.
- Common failures and fixes.

## Acceptance Criteria

- A fresh developer can follow the doc from `.env` to working RAG retrieval.
- The doc distinguishes "service running" from "RAG data ready".
- Demo failure modes are explainable without reading source code.
- Manual smoke test confirms indexed chunks before a recorded demo.
