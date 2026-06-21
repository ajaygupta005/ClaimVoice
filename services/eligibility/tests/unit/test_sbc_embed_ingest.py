"""Unit tests for sbc_embed_ingest chunk_text helper."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the ingest script importable without installing it as a package
sys.path.insert(0, str(Path(__file__).parents[5] / "data" / "ingest"))

from sbc_embed_ingest import chunk_text  # noqa: E402


# ---------------------------------------------------------------------------
# Basic windowing
# ---------------------------------------------------------------------------

def test_chunk_text_basic() -> None:
    """800-word input with chunk_size=400, overlap=50 → 2 chunks."""
    text = " ".join(f"word{i}" for i in range(800))
    chunks = chunk_text(text, chunk_size=400, overlap=50)
    assert len(chunks) == 2
    # First chunk: words 0–399
    assert chunks[0].split()[0] == "word0"
    assert chunks[0].split()[-1] == "word399"
    # Second chunk: words 350–799
    assert chunks[1].split()[0] == "word350"
    assert chunks[1].split()[-1] == "word799"


def test_chunk_text_overlap_shared_words() -> None:
    """Overlapping words appear in both adjacent chunks."""
    text = " ".join(f"w{i}" for i in range(500))
    chunks = chunk_text(text, chunk_size=400, overlap=50)
    assert len(chunks) == 2
    last_of_first = set(chunks[0].split()[-50:])
    first_of_second = set(chunks[1].split()[:50])
    assert last_of_first == first_of_second


def test_chunk_text_exact_window() -> None:
    """Input == chunk_size → exactly 1 chunk."""
    text = " ".join(f"word{i}" for i in range(400))
    chunks = chunk_text(text, chunk_size=400, overlap=50)
    assert len(chunks) == 1
    assert len(chunks[0].split()) == 400


def test_chunk_text_shorter_than_window() -> None:
    """Input shorter than chunk_size → exactly 1 chunk with all words."""
    text = " ".join(f"word{i}" for i in range(100))
    chunks = chunk_text(text, chunk_size=400, overlap=50)
    assert len(chunks) == 1
    assert len(chunks[0].split()) == 100


def test_chunk_text_empty() -> None:
    """Empty string → empty list."""
    assert chunk_text("") == []


def test_chunk_text_whitespace_only() -> None:
    """Whitespace-only string → empty list."""
    assert chunk_text("   \n\t  ") == []


def test_chunk_text_single_word() -> None:
    """Single word → one chunk."""
    chunks = chunk_text("hello", chunk_size=400, overlap=50)
    assert chunks == ["hello"]


def test_chunk_text_three_chunks() -> None:
    """Input large enough to produce 3 chunks."""
    # With chunk_size=400, overlap=50, step=350:
    # chunk 0: 0–399, chunk 1: 350–749, chunk 2: 700–1049
    text = " ".join(f"w{i}" for i in range(1050))
    chunks = chunk_text(text, chunk_size=400, overlap=50)
    assert len(chunks) == 3
    assert chunks[0].split()[0] == "w0"
    assert chunks[2].split()[-1] == "w1049"


def test_chunk_text_no_overlap() -> None:
    """overlap=0 → non-overlapping windows, no shared words."""
    text = " ".join(f"w{i}" for i in range(800))
    chunks = chunk_text(text, chunk_size=400, overlap=0)
    assert len(chunks) == 2
    assert chunks[0].split()[-1] == "w399"
    assert chunks[1].split()[0] == "w400"
