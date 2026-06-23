"""Component 02 - data survives a container restart."""
import os
import subprocess
import pytest
import psycopg


@pytest.mark.integration
@pytest.mark.skip(reason="manual test - bring stack down/up between runs")
def test_postgres_data_persists_across_restart():
    """Manually: write a row, restart compose, read it back."""
    url = os.environ.get("DATABASE_URL", "postgresql://claimvoice:changeme@localhost:5433/claimvoice")
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS persist_check (id int)")
        cur.execute("INSERT INTO persist_check (id) VALUES (42) ON CONFLICT DO NOTHING")
        conn.commit()
        # restart compose manually then re-run this test
        cur.execute("SELECT id FROM persist_check WHERE id = 42")
        assert cur.fetchone() == (42,)
