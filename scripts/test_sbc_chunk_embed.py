#!/usr/bin/env python3
"""
Standalone SBC chunk + embed test.

Downloads SBC PDFs (if not already present), extracts text with pdfplumber,
chunks it, embeds with Voyage AI voyage-4-large, and prints size stats.
No database, no Docker, no document_ai model required.

Install deps first:
    pip install voyageai pdfplumber hydra-core omegaconf

Run:
    # Set your key, then:
    python scripts/test_sbc_chunk_embed.py

    # Skip download if PDFs already exist:
    python scripts/test_sbc_chunk_embed.py --no-download

Output:
    - Per-PDF chunk counts printed to stdout
    - data/processed/sbc_chunks_test.json  (chunks + first 8 dims of each vector)
    - Summary: total chunks, vector dims, estimated DB size
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parents[1]
SBC_DIR   = REPO_ROOT / "data" / "raw" / "sbcs"
OUT_FILE  = REPO_ROOT / "data" / "processed" / "sbc_chunks_test.json"

# Same parameters as sbc_embed_ingest.yaml
CHUNK_SIZE     = 400
OVERLAP        = 50
MIN_WORDS      = 20
VOYAGE_MODEL   = "voyage-4-large"
BATCH_SIZE     = 3        # 3 chunks × ~520 tokens ≈ 1560 tokens — well under 10K TPM
BATCH_SLEEP_S  = 22.0     # 22 s → ~2.7 req/min, safely under 3 RPM free-tier limit


# ---------------------------------------------------------------------------
# Chunking (copied from sbc_embed_ingest.py — no import needed)
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    step = chunk_size - overlap
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += step
    return chunks


# ---------------------------------------------------------------------------
# PDF text extraction (pdfplumber, no LayoutLMv3 needed)
# ---------------------------------------------------------------------------

def extract_text(pdf_path: Path) -> str | None:
    """Return extracted text, or None if the file is not a valid PDF."""
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed. Run: pip install pdfplumber")
        sys.exit(1)

    # Quick magic-bytes check — HTML redirect/404 pages start with '<'
    header = pdf_path.read_bytes()[:5]
    if not header.startswith(b"%PDF"):
        logger.warning("  SKIP %s — not a valid PDF (starts with %r)", pdf_path.name, header)
        return None

    try:
        pages: list[str] = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages.append(text)
        return "\n".join(pages)
    except Exception as exc:
        logger.warning("  SKIP %s — pdfplumber error: %s", pdf_path.name, exc)
        return None


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_pdfs() -> None:
    logger.info("Running sbc_download.py ...")
    import subprocess
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "data" / "ingest" / "sbc_download.py")],
        cwd=str(REPO_ROOT),
        capture_output=False,
    )
    if result.returncode != 0:
        logger.error("sbc_download.py failed (exit %d)", result.returncode)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def embed_all(texts: list[str], api_key: str) -> list[list[float]]:
    try:
        import voyageai
    except ImportError:
        logger.error("voyageai not installed. Run: pip install voyageai")
        sys.exit(1)

    client = voyageai.Client(api_key=api_key)
    all_embeddings: list[list[float]] = []
    total_batches = -(-len(texts) // BATCH_SIZE)

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i: i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        logger.info("Embedding batch %d / %d  (%d texts) ...", batch_num, total_batches, len(batch))

        for attempt in range(1, 4):
            try:
                result = client.embed(batch, model=VOYAGE_MODEL, input_type="document")
                all_embeddings.extend(result.embeddings)
                break
            except Exception as exc:
                if attempt < 3 and ("rate" in str(exc).lower() or "limit" in str(exc).lower()):
                    wait = 65 * attempt
                    logger.warning("Rate limit hit — waiting %ds before retry %d/3", wait, attempt + 1)
                    time.sleep(wait)
                else:
                    logger.error("Voyage API error: %s", exc)
                    raise

        if i + BATCH_SIZE < len(texts):
            logger.info("  Sleeping %ds (TPM window reset) ...", int(BATCH_SLEEP_S))
            time.sleep(BATCH_SLEEP_S)

    return all_embeddings


# ---------------------------------------------------------------------------
# Size estimate
# ---------------------------------------------------------------------------

def estimate_storage(n_rows: int, dims: int) -> dict[str, str]:
    bytes_per_vector  = dims * 4                          # float32
    bytes_per_text    = CHUNK_SIZE * 6                    # ~6 bytes/word avg
    bytes_per_meta    = 200
    bytes_per_row     = bytes_per_vector + bytes_per_text + bytes_per_meta
    table_bytes       = n_rows * bytes_per_row
    hnsw_bytes        = int(n_rows * bytes_per_vector * 1.5)  # ~1.5x vector data
    total_bytes       = table_bytes + hnsw_bytes

    def fmt(b: int) -> str:
        if b < 1024:
            return f"{b} B"
        if b < 1024 ** 2:
            return f"{b/1024:.1f} KB"
        return f"{b/1024**2:.2f} MB"

    return {
        "rows":        str(n_rows),
        "vector_dims": str(dims),
        "table_size":  fmt(table_bytes),
        "hnsw_index":  fmt(hnsw_bytes),
        "total":       fmt(total_bytes),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-download", action="store_true",
                        help="Skip sbc_download.py (PDFs already present)")
    args = parser.parse_args()

    api_key = os.environ.get("VOYAGE_API_KEY", "")
    if not api_key:
        logger.error(
            "VOYAGE_API_KEY is not set.\n"
            "  Windows PowerShell : $env:VOYAGE_API_KEY = 'your_key'\n"
            "  Windows CMD        : set VOYAGE_API_KEY=your_key\n"
            "  Mac/Linux          : export VOYAGE_API_KEY=your_key"
        )
        sys.exit(1)

    # Step 1 — Download PDFs
    if not args.no_download:
        download_pdfs()
    else:
        logger.info("Skipping download (--no-download)")

    pdf_files = sorted(SBC_DIR.glob("*.pdf"))
    if not pdf_files:
        logger.error("No PDFs found in %s. Remove --no-download or check sbc_download.py.", SBC_DIR)
        sys.exit(1)

    logger.info("Found %d PDF(s): %s", len(pdf_files), [p.name for p in pdf_files])

    # Step 2 — Extract text + chunk
    all_texts:  list[str] = []
    all_meta:   list[dict] = []

    for pdf_path in pdf_files:
        logger.info("Extracting text from %s ...", pdf_path.name)
        full_text = extract_text(pdf_path)
        if full_text is None:
            continue
        word_count = len(full_text.split())
        logger.info("  %s → %d words", pdf_path.name, word_count)

        if word_count < MIN_WORDS:
            logger.warning("  Skipping — too short (%d words)", word_count)
            continue

        chunks = chunk_text(full_text)
        logger.info("  → %d chunks", len(chunks))

        for idx, chunk in enumerate(chunks):
            all_texts.append(chunk)
            all_meta.append({
                "source_file": pdf_path.name,
                "chunk_index": idx,
                "word_count":  len(chunk.split()),
            })

    logger.info("Total chunks to embed: %d", len(all_texts))

    if not all_texts:
        logger.error("No chunks produced. Check PDFs are readable text (not scanned images).")
        sys.exit(1)

    # Step 3 — Embed
    logger.info("Calling Voyage AI %s ...", VOYAGE_MODEL)
    embeddings = embed_all(all_texts, api_key)

    dims = len(embeddings[0]) if embeddings else 0
    logger.info("Embeddings received: %d vectors × %d dims", len(embeddings), dims)

    # Step 4 — Save output
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output = []
    for meta, text, emb in zip(all_meta, all_texts, embeddings):
        output.append({
            **meta,
            "chunk_text_preview": text[:120] + "..." if len(text) > 120 else text,
            "embedding_preview":  emb[:8],   # first 8 dims only (full vector is large)
            "embedding_dims":     len(emb),
        })

    OUT_FILE.write_text(json.dumps(output, indent=2))
    logger.info("Sample output saved → %s", OUT_FILE)

    # Step 5 — Print size summary
    stats = estimate_storage(len(embeddings), dims)
    print("\n" + "=" * 55)
    print("  SBC CHUNK + EMBED RESULTS")
    print("=" * 55)
    print(f"  PDFs processed   : {len(pdf_files)}")
    print(f"  Total chunks     : {stats['rows']}")
    print(f"  Vector dims      : {stats['vector_dims']}  (voyage-4-large @ 1024)")
    print(f"  Est. table size  : {stats['table_size']}")
    print(f"  Est. HNSW index  : {stats['hnsw_index']}")
    print(f"  Est. total DB    : {stats['total']}")
    print("=" * 55)
    print(f"  Full output      : {OUT_FILE}")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    main()
