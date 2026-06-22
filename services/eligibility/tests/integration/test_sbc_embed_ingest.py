"""Integration tests for sbc_embed_ingest — require a live DB.

Embeddings default to Azure OpenAI (SBC_EMBED_PROVIDER=azure). The ingest tests
stub the embedder, so they need neither an API key nor network access; only the
pgvector similarity test calls a real provider (gated on AZURE_OPENAI_API_KEY).
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parents[4] / "data" / "ingest"))

from sbc_embed_ingest import (  # noqa: E402
    _Embedder,
    bulk_insert_chunks,
    ingest_pdf,
    resolve_plan_id,
)

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

AETNA_PDF = (
    Path(__file__).parents[4] / "data" / "raw" / "sbcs" / "aetna_aetna_bronze_6850.pdf"
)

FIXED_PLAN_ID = uuid.UUID("aaaaaaaa-0001-0001-0001-000000000001")
# Test-only marketing name: unique so it never collides with real seeded plans
# (the fixture owns this row by FIXED_PLAN_ID and resolves it by this name).
FIXED_PLAN_NAME = "ZZ ClaimVoice Test Fixture Plan"


@pytest.fixture()
def db_conn():
    """Live psycopg connection; rolls back after each test."""
    import psycopg

    url = os.environ.get(
        "DATABASE_URL", "postgresql://claimvoice:changeme@localhost:5432/claimvoice"
    )
    with psycopg.connect(url) as conn:
        # Seed a plan row with a fixed UUID so resolve_plan_id works
        conn.execute(
            """
            INSERT INTO plans (id, plan_marketing_name, issuer_name, plan_year, metal_level)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (str(FIXED_PLAN_ID), FIXED_PLAN_NAME, "Aetna", 2026, "Bronze"),
        )
        conn.commit()

        yield conn

        # Cleanup: remove test rows
        conn.execute("DELETE FROM sbc_chunks WHERE plan_id = %s", (str(FIXED_PLAN_ID),))
        conn.execute(
            "DELETE FROM plans WHERE id = %s", (str(FIXED_PLAN_ID),)
        )
        conn.commit()


@pytest.fixture()
def fake_embedder():
    """Embedder stub: returns one deterministic 1024-dim zero vector per input text."""
    emb = MagicMock()
    emb.embed.side_effect = lambda texts: [[0.0] * 1024 for _ in texts]
    return emb


def _ingest_cfg():
    """Minimal cfg with the fields ingest_pdf reads for chunking/batching."""
    from omegaconf import OmegaConf

    return OmegaConf.create(
        {
            "embed": {
                "chunk_size": 400,
                "overlap": 50,
                "min_chunk_words": 20,
                "voyage_batch_size": 128,
                "voyage_sleep_s": 0.0,
            }
        }
    )


# ---------------------------------------------------------------------------
# resolve_plan_id
# ---------------------------------------------------------------------------

def test_resolve_plan_id_found(db_conn) -> None:
    plan_id = resolve_plan_id(db_conn, FIXED_PLAN_NAME)
    assert plan_id == FIXED_PLAN_ID


def test_resolve_plan_id_case_insensitive(db_conn) -> None:
    plan_id = resolve_plan_id(db_conn, FIXED_PLAN_NAME.lower())
    assert plan_id == FIXED_PLAN_ID


def test_resolve_plan_id_not_found(db_conn) -> None:
    plan_id = resolve_plan_id(db_conn, "Nonexistent Plan XYZ")
    assert plan_id is None


# ---------------------------------------------------------------------------
# bulk_insert_chunks
# ---------------------------------------------------------------------------

def test_bulk_insert_idempotent(db_conn) -> None:
    """Inserting the same chunk twice produces exactly 1 row."""
    rows = [
        {
            "source_file": "test.pdf",
            "section_name": "benefits",
            "chunk_index": 0,
            "chunk_text": "Primary care visit $30 copay",
            "embedding": [0.1] * 1024,
            "page_number": None,
        }
    ]
    bulk_insert_chunks(db_conn, FIXED_PLAN_ID, "test.pdf", rows)
    db_conn.commit()
    bulk_insert_chunks(db_conn, FIXED_PLAN_ID, "test.pdf", rows)
    db_conn.commit()

    count = db_conn.execute(
        "SELECT COUNT(*) FROM sbc_chunks WHERE plan_id = %s AND source_file = 'test.pdf'",
        (str(FIXED_PLAN_ID),),
    ).fetchone()[0]
    assert count == 1


def test_bulk_insert_multiple_chunks(db_conn) -> None:
    """Two chunks with different indices both inserted."""
    rows = [
        {
            "source_file": "multi.pdf",
            "section_name": "cost_sharing",
            "chunk_index": 0,
            "chunk_text": "Deductible $1500",
            "embedding": [0.2] * 1024,
            "page_number": 1,
        },
        {
            "source_file": "multi.pdf",
            "section_name": "cost_sharing",
            "chunk_index": 1,
            "chunk_text": "Out of pocket max $5000",
            "embedding": [0.3] * 1024,
            "page_number": 2,
        },
    ]
    bulk_insert_chunks(db_conn, FIXED_PLAN_ID, "multi.pdf", rows)
    db_conn.commit()

    count = db_conn.execute(
        "SELECT COUNT(*) FROM sbc_chunks WHERE plan_id = %s AND source_file = 'multi.pdf'",
        (str(FIXED_PLAN_ID),),
    ).fetchone()[0]
    assert count == 2


# ---------------------------------------------------------------------------
# ingest_pdf (end-to-end with a stubbed embedder)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not AETNA_PDF.exists(), reason="Aetna Bronze SBC PDF not downloaded")
def test_ingest_pdf_inserts_rows(db_conn, fake_embedder) -> None:
    """ingest_pdf creates sbc_chunks rows for the Aetna Bronze PDF."""
    ingest_pdf(db_conn, fake_embedder, _ingest_cfg(), AETNA_PDF, FIXED_PLAN_NAME, {})
    db_conn.commit()

    count = db_conn.execute(
        "SELECT COUNT(*) FROM sbc_chunks WHERE plan_id = %s",
        (str(FIXED_PLAN_ID),),
    ).fetchone()[0]
    assert count > 0, "Expected at least one chunk to be inserted"


@pytest.mark.skipif(not AETNA_PDF.exists(), reason="Aetna Bronze SBC PDF not downloaded")
def test_ingest_pdf_idempotent(db_conn, fake_embedder) -> None:
    """Running ingest_pdf twice produces the same row count."""
    cfg = _ingest_cfg()

    ingest_pdf(db_conn, fake_embedder, cfg, AETNA_PDF, FIXED_PLAN_NAME, {})
    db_conn.commit()
    count_after_first = db_conn.execute(
        "SELECT COUNT(*) FROM sbc_chunks WHERE plan_id = %s", (str(FIXED_PLAN_ID),)
    ).fetchone()[0]

    ingest_pdf(db_conn, fake_embedder, cfg, AETNA_PDF, FIXED_PLAN_NAME, {})
    db_conn.commit()
    count_after_second = db_conn.execute(
        "SELECT COUNT(*) FROM sbc_chunks WHERE plan_id = %s", (str(FIXED_PLAN_ID),)
    ).fetchone()[0]

    assert count_after_first == count_after_second, "Second run must not insert new rows"


# ---------------------------------------------------------------------------
# pgvector sanity query (requires a real embedding provider — Azure by default)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("AZURE_OPENAI_API_KEY"),
    reason="AZURE_OPENAI_API_KEY not set — skipping live embedding test",
)
@pytest.mark.skipif(not AETNA_PDF.exists(), reason="Aetna Bronze SBC PDF not downloaded")
def test_pgvector_similarity_query(db_conn) -> None:
    """Embed real chunks + a real query (same provider) and assert a close match."""
    from omegaconf import OmegaConf

    cfg = OmegaConf.create(
        {
            "embed": {
                "provider": os.environ.get("SBC_EMBED_PROVIDER", "azure"),
                "embed_dimensions": 1024,
                "azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
                "azure_api_key": os.environ.get("AZURE_OPENAI_API_KEY", ""),
                "azure_api_version": os.environ.get(
                    "AZURE_OPENAI_API_VERSION", "2024-12-01-preview"
                ),
                "azure_deployment": os.environ.get(
                    "FOUNDRY_DEPLOYMENT_EMBEDDING", "text-embedding-3-large"
                ),
                "voyage_api_key": os.environ.get("VOYAGE_API_KEY", ""),
                "voyage_model": "voyage-4-large",
                "chunk_size": 400,
                "overlap": 50,
                "min_chunk_words": 20,
                "voyage_batch_size": 128,
                "voyage_sleep_s": 0.0,
            }
        }
    )
    embedder = _Embedder(cfg)

    # Ingest real (provider-embedded) chunks for the fixed plan
    ingest_pdf(db_conn, embedder, cfg, AETNA_PDF, FIXED_PLAN_NAME, {})
    db_conn.commit()

    query = "Is physical therapy covered?"
    query_vec = embedder.embed([query])[0]
    query_vec_str = "[" + ",".join(str(v) for v in query_vec) + "]"

    row = db_conn.execute(
        """
        SELECT chunk_text, embedding <=> %s::vector AS dist
        FROM sbc_chunks
        WHERE plan_id = %s
        ORDER BY embedding <=> %s::vector
        LIMIT 1
        """,
        (query_vec_str, str(FIXED_PLAN_ID), query_vec_str),
    ).fetchone()

    assert row is not None, "No chunks found — ingest_pdf should have inserted some"
    _chunk_text, dist = row
    assert dist < 0.8, f"Top result cosine distance {dist:.3f} is too large"
