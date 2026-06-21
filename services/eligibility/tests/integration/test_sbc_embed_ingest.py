"""Integration tests for sbc_embed_ingest — require a live DB and VOYAGE_API_KEY."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[5] / "data" / "ingest"))

from sbc_embed_ingest import (  # noqa: E402
    bulk_insert_chunks,
    chunk_text,
    embed_batch,
    ingest_pdf,
    resolve_plan_id,
)

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

AETNA_PDF = (
    Path(__file__).parents[5] / "data" / "raw" / "sbcs" / "aetna_aetna_bronze_6850.pdf"
)

FIXED_PLAN_ID = uuid.UUID("aaaaaaaa-0001-0001-0001-000000000001")
FIXED_PLAN_NAME = "Aetna Bronze 6850"


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
def fake_voyage_client():
    """Voyage client that returns deterministic 1024-dim zero vectors."""
    client = MagicMock()
    client.embed.return_value = MagicMock(
        embeddings=[[0.0] * 1024]
    )
    return client


# ---------------------------------------------------------------------------
# resolve_plan_id
# ---------------------------------------------------------------------------

def test_resolve_plan_id_found(db_conn) -> None:
    plan_id = resolve_plan_id(db_conn, FIXED_PLAN_NAME)
    assert plan_id == FIXED_PLAN_ID


def test_resolve_plan_id_case_insensitive(db_conn) -> None:
    plan_id = resolve_plan_id(db_conn, "aetna bronze 6850")
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
# ingest_pdf (end-to-end with mocked Voyage)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not AETNA_PDF.exists(), reason="Aetna Bronze SBC PDF not downloaded")
def test_ingest_pdf_inserts_rows(db_conn, fake_voyage_client, tmp_path) -> None:
    """ingest_pdf creates sbc_chunks rows for the Aetna Bronze PDF."""
    from omegaconf import OmegaConf

    cfg = OmegaConf.create({
        "embed": {
            "chunk_size": 400,
            "overlap": 50,
            "min_chunk_words": 20,
            "voyage_model": "voyage-4-large",
            "voyage_batch_size": 128,
            "voyage_sleep_s": 0.0,
        }
    })

    # Patch embed_batch so it always returns a valid 1024-dim vector per text
    with patch(
        "sbc_embed_ingest.embed_batch",
        side_effect=lambda client, texts, model: [[0.0] * 1024 for _ in texts],
    ):
        ingest_pdf(db_conn, fake_voyage_client, cfg, AETNA_PDF, FIXED_PLAN_NAME)
        db_conn.commit()

    count = db_conn.execute(
        "SELECT COUNT(*) FROM sbc_chunks WHERE plan_id = %s",
        (str(FIXED_PLAN_ID),),
    ).fetchone()[0]
    assert count > 0, "Expected at least one chunk to be inserted"


@pytest.mark.skipif(not AETNA_PDF.exists(), reason="Aetna Bronze SBC PDF not downloaded")
def test_ingest_pdf_idempotent(db_conn, fake_voyage_client) -> None:
    """Running ingest_pdf twice produces the same row count."""
    from omegaconf import OmegaConf

    cfg = OmegaConf.create({
        "embed": {
            "chunk_size": 400,
            "overlap": 50,
            "min_chunk_words": 20,
            "voyage_model": "voyage-4-large",
            "voyage_batch_size": 128,
            "voyage_sleep_s": 0.0,
        }
    })

    with patch(
        "sbc_embed_ingest.embed_batch",
        side_effect=lambda client, texts, model: [[0.0] * 1024 for _ in texts],
    ):
        ingest_pdf(db_conn, fake_voyage_client, cfg, AETNA_PDF, FIXED_PLAN_NAME)
        db_conn.commit()
        count_after_first = db_conn.execute(
            "SELECT COUNT(*) FROM sbc_chunks WHERE plan_id = %s", (str(FIXED_PLAN_ID),)
        ).fetchone()[0]

        ingest_pdf(db_conn, fake_voyage_client, cfg, AETNA_PDF, FIXED_PLAN_NAME)
        db_conn.commit()
        count_after_second = db_conn.execute(
            "SELECT COUNT(*) FROM sbc_chunks WHERE plan_id = %s", (str(FIXED_PLAN_ID),)
        ).fetchone()[0]

    assert count_after_first == count_after_second, "Second run must not insert new rows"


# ---------------------------------------------------------------------------
# pgvector sanity query (requires real VOYAGE_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("VOYAGE_API_KEY"),
    reason="VOYAGE_API_KEY not set — skipping live Voyage API test",
)
@pytest.mark.skipif(not AETNA_PDF.exists(), reason="Aetna Bronze SBC PDF not downloaded")
def test_pgvector_similarity_query(db_conn) -> None:
    """Embed a real query and assert top result is semantically close."""
    import voyageai

    api_key = os.environ["VOYAGE_API_KEY"]
    client = voyageai.Client(api_key=api_key)

    query = "Is physical therapy covered?"
    result = client.embed([query], model="voyage-4-large", input_type="query")
    query_vec = result.embeddings[0]
    query_vec_str = "[" + ",".join(str(v) for v in query_vec) + "]"

    row = db_conn.execute(
        f"""
        SELECT chunk_text, embedding <=> %s::vector AS dist
        FROM sbc_chunks
        WHERE plan_id = %s
        ORDER BY embedding <=> %s::vector
        LIMIT 1
        """,
        (query_vec_str, str(FIXED_PLAN_ID), query_vec_str),
    ).fetchone()

    assert row is not None, "No chunks found — run ingest_pdf first"
    _chunk_text, dist = row
    assert dist < 0.5, f"Top result cosine distance {dist:.3f} is too large"
