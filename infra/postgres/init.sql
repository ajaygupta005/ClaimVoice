-- pgvector is deferred to WS-4 (SBC RAG). The stock postgis/postgis image does
-- NOT ship the "vector" extension, so enabling it here fails container init.
-- When WS-4 adds SBC embeddings, switch to an image that bundles pgvector and
-- re-enable the line below.
-- CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
