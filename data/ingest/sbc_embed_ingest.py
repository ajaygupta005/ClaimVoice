#!/usr/bin/env python3
"""
SBC Chunk & Embed Ingest: Parse SBC PDFs, chunk section text, embed with
Voyage AI voyage-4-large, and store in the sbc_chunks pgvector table.

Must run after:
  - alembic upgrade head  (creates sbc_chunks table)
  - sbc_download.py       (downloads PDFs to data/raw/sbcs/)
  - plan_puf_ingest.py    (populates plans table for plan_id resolution)

Usage:
    python data/ingest/sbc_embed_ingest.py
    python data/ingest/sbc_embed_ingest.py embed.sbc_dir=data/raw/sbcs
    python data/ingest/sbc_embed_ingest.py embed.chunk_size=300 embed.overlap=40
"""

from __future__ import annotations

import hashlib
import logging
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
import voyageai
from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """Split text into overlapping word-count windows.

    chunk_size=400 words ≈ 512 tokens for English prose.
    overlap=50 words preserves sentence context across chunk boundaries.
    Returns [] for empty or whitespace-only input.
    """
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += step
    return chunks


# ---------------------------------------------------------------------------
# Voyage AI embedding
# ---------------------------------------------------------------------------

def embed_batch(
    client: voyageai.Client,
    texts: list[str],
    model: str,
) -> list[list[float]]:
    """Embed a batch of texts using Voyage AI. Returns one vector per text."""
    result = client.embed(texts, model=model, input_type="document")
    return result.embeddings


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def resolve_plan_id(conn: psycopg.Connection, plan_name: str) -> uuid.UUID | None:
    """Case-insensitive lookup of plan_id by plan_marketing_name."""
    row = conn.execute(
        "SELECT id FROM plans WHERE LOWER(plan_marketing_name) = LOWER(%s) LIMIT 1",
        (plan_name,),
    ).fetchone()
    if row is None:
        logger.warning("No plan found for name %r — skipping PDF", plan_name)
        return None
    return row[0]


def _write_audit_log(
    conn: psycopg.Connection,
    source_file: str,
    data_hash: str,
    row_count: int,
) -> None:
    conn.execute(
        """
        INSERT INTO audit_log (table_name, record_id, source, data_hash, notes)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            "sbc_chunks",
            source_file,
            "sbc_embed_ingest",
            data_hash,
            f"inserted_or_skipped={row_count} chunks",
        ),
    )


def bulk_insert_chunks(
    conn: psycopg.Connection,
    plan_id: uuid.UUID,
    source_file: str,
    rows: list[dict[str, Any]],
) -> int:
    """Insert chunk rows with ON CONFLICT DO NOTHING. Returns rows attempted."""
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO sbc_chunks
                (plan_id, source_file, section_name, chunk_index, chunk_text, embedding, page_number)
            VALUES
                (%s, %s, %s, %s, %s, %s::vector, %s)
            ON CONFLICT (plan_id, source_file, section_name, chunk_index) DO NOTHING
            """,
            [
                (
                    str(plan_id),
                    r["source_file"],
                    r["section_name"],
                    r["chunk_index"],
                    r["chunk_text"],
                    str(r["embedding"]),
                    r.get("page_number"),
                )
                for r in rows
            ],
        )
    return len(rows)


# ---------------------------------------------------------------------------
# Per-PDF orchestration
# ---------------------------------------------------------------------------

def ingest_pdf(
    conn: psycopg.Connection,
    voyage_client: voyageai.Client,
    cfg: Any,
    pdf_path: Path,
    plan_name: str,
    last_embed_time: dict,
) -> None:
    """Parse one PDF, chunk, embed, and insert into sbc_chunks."""
    logger.info("Processing %s (plan=%r)", pdf_path.name, plan_name)

    plan_id = resolve_plan_id(conn, plan_name)
    if plan_id is None:
        return

    # SHA256 of the PDF bytes for audit_log
    pdf_bytes = pdf_path.read_bytes()
    data_hash = hashlib.sha256(pdf_bytes).hexdigest()

    # Parse PDF into sections — SBCParserRunner preferred, pdfplumber fallback
    parsed_sections: list[dict] | None = None
    try:
        from document_ai.inference.sbc_parser_runner import SBCParserRunner
        try:
            parsed = SBCParserRunner()(str(pdf_path), document_id=pdf_path.stem)
            parsed_sections = parsed.get("sections", [])
            logger.info("  Parsed with SBCParserRunner (%d sections)", len(parsed_sections))
        except Exception as exc:
            logger.error("SBCParserRunner failed for %s: %s", pdf_path.name, exc)
            return
    except ImportError:
        logger.info("  document_ai not available — falling back to pdfplumber")

    if parsed_sections is None:
        try:
            import pdfplumber
        except ImportError:
            logger.error(
                "Neither document_ai nor pdfplumber installed. Run: pip install pdfplumber"
            )
            return
        header = pdf_bytes[:5]
        if not header.startswith(b"%PDF"):
            logger.warning("  %s is not a valid PDF, skipping.", pdf_path.name)
            return
        try:
            pages: list[str] = []
            with pdfplumber.open(str(pdf_path)) as pdf:
                for page in pdf.pages:
                    pages.append(page.extract_text() or "")
            parsed_sections = [{"section_name": "full_document", "raw_text": "\n".join(pages)}]
        except Exception as exc:
            logger.error("pdfplumber failed for %s: %s", pdf_path.name, exc)
            return

    # Build chunk records
    all_chunks: list[str] = []
    chunk_meta: list[dict[str, Any]] = []

    for section in parsed_sections:
        raw_text: str = section.get("raw_text", "")
        section_name: str = section.get("section_name", "unknown")
        words = raw_text.split()

        if len(words) < cfg.embed.min_chunk_words:
            logger.debug(
                "Skipping section %r in %s — only %d words (min=%d)",
                section_name, pdf_path.name, len(words), cfg.embed.min_chunk_words,
            )
            continue

        chunks = chunk_text(raw_text, cfg.embed.chunk_size, cfg.embed.overlap)
        for idx, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            chunk_meta.append({
                "source_file": pdf_path.name,
                "section_name": section_name,
                "chunk_index": idx,
                "chunk_text": chunk,
                "page_number": None,  # SBCParserRunner doesn't track per-chunk page
            })

    if not all_chunks:
        logger.warning("No chunks produced for %s — all sections too short", pdf_path.name)
        return

    logger.info(
        "%s → %d chunks across %d sections",
        pdf_path.name, len(all_chunks),
        len({m["section_name"] for m in chunk_meta}),
    )

    # Embed in batches
    batch_size: int = cfg.embed.voyage_batch_size
    sleep_s: float = cfg.embed.voyage_sleep_s
    all_embeddings: list[list[float]] = []

    for batch_start in range(0, len(all_chunks), batch_size):
        batch = all_chunks[batch_start: batch_start + batch_size]

        # Enforce rate limit across PDFs by tracking last embed time globally
        elapsed = time.monotonic() - last_embed_time.get("t", 0.0)
        gap = sleep_s - elapsed
        if gap > 0:
            logger.debug("Rate-limit sleep %.1fs before batch %d", gap, batch_start)
            time.sleep(gap)

        logger.debug(
            "Embedding batch %d/%d (%d texts)",
            batch_start // batch_size + 1,
            -(-len(all_chunks) // batch_size),
            len(batch),
        )
        for attempt in range(4):
            try:
                embeddings = embed_batch(voyage_client, batch, cfg.embed.voyage_model)
                last_embed_time["t"] = time.monotonic()
                break
            except Exception as exc:
                err_str = str(exc).lower()
                if ("rate" in err_str or "429" in err_str) and attempt < 3:
                    wait = sleep_s * (2 ** (attempt + 1))
                    logger.warning(
                        "Rate limited on batch %d; retrying in %.1fs (attempt %d/3)",
                        batch_start, wait, attempt + 1,
                    )
                    time.sleep(wait)
                    last_embed_time["t"] = time.monotonic()
                else:
                    logger.error(
                        "Voyage API failed for batch starting at %d: %s", batch_start, exc
                    )
                    return
        else:
            logger.error("Exhausted retries for batch starting at %d", batch_start)
            return
        all_embeddings.extend(embeddings)

    # Attach embeddings to metadata rows
    rows = []
    for meta, embedding in zip(chunk_meta, all_embeddings):
        rows.append({**meta, "embedding": embedding})

    # Bulk insert (idempotent)
    attempted = bulk_insert_chunks(conn, plan_id, pdf_path.name, rows)
    _write_audit_log(conn, pdf_path.name, data_hash, attempted)
    conn.commit()

    logger.info(
        "Done %s: %d chunk rows attempted (dupes silently skipped)",
        pdf_path.name, attempted,
    )


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def _load_manifest(cfg: Any) -> dict[str, str]:
    """Return {pdf_filename: plan_name} from sbc_manifest.yaml sidecar JSONs.

    Each downloaded PDF has a sibling .json sidecar written by sbc_download.py
    containing {plan_name, payor, ...}. We read those to resolve plan names
    without duplicating the manifest YAML path.
    """
    import json

    sbc_dir = Path(cfg.embed.sbc_dir)
    mapping: dict[str, str] = {}
    for json_path in sbc_dir.glob("*.json"):
        try:
            data = json.loads(json_path.read_text())
            pdf_name = json_path.with_suffix(".pdf").name
            plan_name = data.get("plan_name", "")
            if plan_name:
                mapping[pdf_name] = plan_name
        except Exception as exc:
            logger.warning("Could not read sidecar %s: %s", json_path.name, exc)
    return mapping


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    config_dir = Path(__file__).parent / "configs"
    with initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = compose(config_name="sbc_embed_ingest", overrides=sys.argv[1:])

    logger.info("Config:\n%s", OmegaConf.to_yaml(cfg))

    voyage_api_key: str = cfg.embed.voyage_api_key
    if not voyage_api_key:
        logger.error(
            "VOYAGE_API_KEY is not set. Export it or add it to .env before running."
        )
        sys.exit(1)

    sbc_dir = Path(cfg.embed.sbc_dir)
    if not sbc_dir.exists():
        logger.error(
            "sbc_dir %r does not exist. Run sbc_download.py first.", str(sbc_dir)
        )
        sys.exit(1)

    pdf_files = sorted(sbc_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning("No PDF files found in %s — nothing to do.", sbc_dir)
        return

    logger.info("Found %d PDF file(s) in %s", len(pdf_files), sbc_dir)

    manifest = _load_manifest(cfg)
    voyage_client = voyageai.Client(api_key=voyage_api_key)

    database_url: str = cfg.embed.database_url
    with psycopg.connect(database_url) as conn:
        processed = skipped = 0
        last_embed_time: dict = {}
        for pdf_path in pdf_files:
            plan_name = manifest.get(pdf_path.name)
            if not plan_name:
                logger.warning(
                    "No sidecar JSON for %s — cannot resolve plan name. Skipping.",
                    pdf_path.name,
                )
                skipped += 1
                continue

            ingest_pdf(conn, voyage_client, cfg, pdf_path, plan_name, last_embed_time)
            processed += 1

    logger.info(
        "sbc_embed_ingest complete: processed=%d skipped=%d",
        processed, skipped,
    )


if __name__ == "__main__":
    main()
