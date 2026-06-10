# Component 02 - Data Layer Infrastructure - Research

> Alternatives considered, decisions made, references.

## Why Postgres 16
- pgvector HNSW index landed with massive perf improvements in Postgres 16.
- Logical replication is now mature (relevant if we ever read-replica).
- Better partition pruning than 15.

## Why pgvector over Qdrant/Weaviate/Pinecone
- **Transactional consistency** with the relational data is the killer feature for our use case. Member records and their embeddings stay in sync.
- One fewer system to operate.
- Free; self-hosted; no per-vector pricing.

## Why PostGIS for provider geo
- Production-grade geospatial; `ST_DWithin` with a GiST index is the right primitive for "providers within X km of point Y".
- Used by everyone from Uber to OpenStreetMap.

## Why MinIO over local filesystem
- S3-compatible API means our DVC remote, our recording store, and our MLflow artifact store all work the same way locally and in production.
- Single binary, easy to operate.

## References
- pgvector: https://github.com/pgvector/pgvector
- PostGIS: https://postgis.net/
- MinIO: https://min.io/docs/minio/container/index.html
- postgis/postgis Docker image: https://hub.docker.com/r/postgis/postgis

