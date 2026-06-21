"""Add sbc_chunks table with pgvector HNSW index.

Revision ID: 002
Revises: 001
Create Date: 2026-06-20 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("""
        CREATE TABLE sbc_chunks (
            id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            plan_id          UUID         NOT NULL
                                          REFERENCES plans(id) ON DELETE CASCADE,
            source_file      TEXT         NOT NULL,
            section_name     TEXT         NOT NULL,
            chunk_index      SMALLINT     NOT NULL,
            chunk_text       TEXT         NOT NULL,
            embedding        vector(1024) NOT NULL,
            page_number      SMALLINT,
            audit_created_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
            UNIQUE (plan_id, source_file, section_name, chunk_index)
        )
    """)
    op.execute("""
        CREATE INDEX sbc_chunks_hnsw_idx
            ON sbc_chunks
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
    """)
    op.execute(
        "CREATE INDEX sbc_chunks_plan_id_idx ON sbc_chunks (plan_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sbc_chunks")
