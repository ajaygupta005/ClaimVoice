"""Component 02 - Postgres has pgvector and PostGIS extensions enabled."""
import os
import pytest
import psycopg


@pytest.mark.integration
def test_pgvector_extension_installed():
    url = os.environ.get("DATABASE_URL", "postgresql://claimvoice:changeme@localhost:5432/claimvoice")
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            row = cur.fetchone()
    assert row is not None, "pgvector extension not installed"


@pytest.mark.integration
def test_postgis_extension_installed():
    url = os.environ.get("DATABASE_URL", "postgresql://claimvoice:changeme@localhost:5432/claimvoice")
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'postgis'")
            row = cur.fetchone()
    assert row is not None, "PostGIS extension not installed"
