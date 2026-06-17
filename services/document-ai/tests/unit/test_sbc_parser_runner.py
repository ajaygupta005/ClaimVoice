from __future__ import annotations

import io
import struct
import zlib
from pathlib import Path

import pytest

from document_ai.inference.sbc_parser_runner import SBCParserRunner, _extract_benefit_rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_pdf(text: str) -> bytes:
    """Build a minimal single-page PDF containing *text* as a text stream."""
    stream = f"BT /F1 12 Tf 50 700 Td ({text}) Tj ET".encode()
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] /Contents 4 0 R "
            b"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 "
            b"/BaseFont /Helvetica >> >> >> >>\nendobj\n"
        ),
        b"4 0 obj\n<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream\nendobj\n",
    ]
    body = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(body))
        body += obj
    xref_offset = len(body)
    xref = b"xref\n0 " + str(len(objects) + 1).encode() + b"\n"
    xref += b"0000000000 65535 f \n"
    for off in offsets:
        xref += str(off).zfill(10).encode() + b" 00000 n \n"
    trailer = (
        b"trailer\n<< /Size "
        + str(len(objects) + 1).encode()
        + b" /Root 1 0 R >>\nstartxref\n"
        + str(xref_offset).encode()
        + b"\n%%EOF\n"
    )
    return body + xref + trailer


# ---------------------------------------------------------------------------
# _extract_benefit_rows unit tests (pure function, no I/O)
# ---------------------------------------------------------------------------


class TestExtractBenefitRows:
    def test_matches_dollar_copay(self):
        lines = ["Primary care visit  $30 copay"]
        rows = _extract_benefit_rows(lines)
        assert len(rows) == 1
        assert rows[0]["service"] == "Primary care visit"
        assert rows[0]["cost"] == "$30"

    def test_matches_percentage(self):
        lines = ["Specialist visit  20%"]
        rows = _extract_benefit_rows(lines)
        assert len(rows) == 1
        assert rows[0]["cost"] == "20%"

    def test_matches_not_covered(self):
        lines = ["Cosmetic surgery  Not Covered"]
        rows = _extract_benefit_rows(lines)
        assert len(rows) == 1
        assert rows[0]["cost"] == "Not Covered"

    def test_single_space_not_matched(self):
        # Regex requires 2+ spaces; single space should not match
        lines = ["Primary care visit $30 copay"]
        rows = _extract_benefit_rows(lines)
        assert rows == []

    def test_empty_lines(self):
        assert _extract_benefit_rows([]) == []
        assert _extract_benefit_rows([""]) == []


# ---------------------------------------------------------------------------
# SBCParserRunner — output contract tests (rule-based fallback path)
# ---------------------------------------------------------------------------


class TestSBCParserRunnerContract:
    @pytest.fixture()
    def runner(self) -> SBCParserRunner:
        # No checkpoint exists → rule-based fallback (no ML required)
        return SBCParserRunner()

    @pytest.fixture()
    def pdf_path(self, tmp_path: Path) -> Path:
        content = (
            "Summary of Benefits and Coverage\n"
            "Plan Overview\n\n"
            "Common Medical Event  Covered Services\n"
            "Primary care visit  $30 copay\n\n"
            "What is not covered\nCosmetic surgery  Not Covered\n"
        )
        p = tmp_path / "test_sbc.pdf"
        p.write_bytes(_minimal_pdf(content))
        return p

    def test_top_level_keys(self, runner: SBCParserRunner, pdf_path: Path):
        result = runner(str(pdf_path), document_id="doc-001")
        assert set(result.keys()) >= {"document_id", "plan_name", "sections"}

    def test_document_id_echoed(self, runner: SBCParserRunner, pdf_path: Path):
        result = runner(str(pdf_path), document_id="doc-42")
        assert result["document_id"] == "doc-42"

    def test_plan_name_is_string(self, runner: SBCParserRunner, pdf_path: Path):
        result = runner(str(pdf_path), document_id="doc-001")
        assert isinstance(result["plan_name"], str)

    def test_sections_is_list(self, runner: SBCParserRunner, pdf_path: Path):
        result = runner(str(pdf_path), document_id="doc-001")
        assert isinstance(result["sections"], list)

    def test_section_keys(self, runner: SBCParserRunner, pdf_path: Path):
        result = runner(str(pdf_path), document_id="doc-001")
        for section in result["sections"]:
            assert set(section.keys()) >= {"section_name", "benefit_rows", "raw_text"}

    def test_mandatory_sections_always_present(self, runner: SBCParserRunner, pdf_path: Path):
        result = runner(str(pdf_path), document_id="doc-001")
        names = {s["section_name"] for s in result["sections"]}
        assert {"plan_summary", "benefits", "coverage_exclusions"}.issubset(names)

    def test_missing_file_raises(self, runner: SBCParserRunner, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            runner(str(tmp_path / "nonexistent.pdf"), document_id="x")
