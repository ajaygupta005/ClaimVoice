from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForTokenClassification, LayoutLMv3Processor

from document_ai.lib.logger import logger

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SERVICE_ROOT = Path(__file__).parents[3]
_DEFAULT_MODEL_DIR = _SERVICE_ROOT / "artifacts" / "sbc_parser" / "latest"
_WEIGHTS_FILENAME = "model.safetensors"

# Canonical section labels the model is trained to emit (BIO-tagged).
# The "O" label is implicit; these are the B-/I- field names.
SECTION_LABELS: list[str] = [
    "plan_summary",
    "benefits",
    "coverage_exclusions",
    "cost_sharing",
    "coverage_period",
    "network_info",
]

# Patterns used for rule-based section detection when no trained model is
# available (model-absent graceful degradation).
_SECTION_PATTERNS: dict[str, re.Pattern] = {
    "plan_summary": re.compile(
        r"(summary of benefits|plan summary|about your plan|plan overview)",
        re.IGNORECASE,
    ),
    "benefits": re.compile(
        r"(common medical event|covered services|what.*plan covers|benefits at a glance)",
        re.IGNORECASE,
    ),
    "coverage_exclusions": re.compile(
        r"(excluded|not covered|exclusion|limitation|what.*not covered)",
        re.IGNORECASE,
    ),
    "cost_sharing": re.compile(
        r"(deductible|out-of-pocket|copay|coinsurance|cost.*sharing)",
        re.IGNORECASE,
    ),
    "coverage_period": re.compile(
        r"(coverage period|plan year|effective date|benefit period)",
        re.IGNORECASE,
    ),
    "network_info": re.compile(
        r"(in-network|out-of-network|provider network|participating provider)",
        re.IGNORECASE,
    ),
}

# Regex for rows that look like a benefit table entry:
#   "Primary care visit   $30 copay / $60 after deductible"
_BENEFIT_ROW_PATTERN = re.compile(
    r"(.{10,80}?)\s{2,}(\$[\d,]+|\d+%|[Nn]ot [Cc]overed|[Nn]/[Aa]|\bno charge\b.{0,30})",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# PDF extraction helpers
# ---------------------------------------------------------------------------


def _extract_pages_pdfplumber(pdf_path: Path) -> list[dict]:
    """Return a list of page dicts with ``text`` and ``words`` keys."""
    import pdfplumber  # optional dep — preferred for layout-rich PDFs

    pages: list[dict] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            words = page.extract_words() or []
            logger.debug(
                f"[sbc_parser] page {page_num}: {len(text)} chars, {len(words)} words"
            )
            pages.append(
                {
                    "page_num": page_num,
                    "text": text,
                    "words": [
                        {
                            "text": w["text"],
                            "bbox": [
                                int(w["x0"]),
                                int(w["top"]),
                                int(w["x1"]),
                                int(w["bottom"]),
                            ],
                        }
                        for w in words
                    ],
                }
            )
    return pages


def _extract_pages_pypdf2(pdf_path: Path) -> list[dict]:
    """Fallback extractor using PyPDF2 (text-only, no layout info)."""
    import PyPDF2  # noqa: N813

    pages: list[dict] = []
    with open(pdf_path, "rb") as fh:
        reader = PyPDF2.PdfReader(fh)
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            logger.debug(f"[sbc_parser] page {page_num} (pypdf2): {len(text)} chars")
            pages.append({"page_num": page_num, "text": text, "words": []})
    return pages


def _extract_pages(pdf_path: Path) -> list[dict]:
    """Try pdfplumber first, fall back to PyPDF2."""
    try:
        return _extract_pages_pdfplumber(pdf_path)
    except ImportError:
        logger.warning("[sbc_parser] pdfplumber not installed; falling back to PyPDF2")
    try:
        return _extract_pages_pypdf2(pdf_path)
    except ImportError as exc:
        raise ImportError(
            "No PDF extraction library found. "
            "Install at least one of: pdfplumber, PyPDF2"
        ) from exc


# ---------------------------------------------------------------------------
# Section detection helpers
# ---------------------------------------------------------------------------


def _rule_based_sections(pages: list[dict]) -> list[dict]:
    """Detect sections using regex patterns when the ML model is unavailable."""
    full_text = "\n".join(p["text"] for p in pages)
    lines = full_text.splitlines()

    # Find the line index where each section header first appears.
    section_starts: list[tuple[int, str]] = []
    for line_idx, line in enumerate(lines):
        for section_name, pattern in _SECTION_PATTERNS.items():
            if pattern.search(line):
                section_starts.append((line_idx, section_name))
                break  # one label per line

    # De-duplicate: keep only the first occurrence of each section label.
    seen: set[str] = set()
    unique_starts: list[tuple[int, str]] = []
    for idx, name in section_starts:
        if name not in seen:
            unique_starts.append((idx, name))
            seen.add(name)

    # Guarantee the three mandatory sections are always present.
    for mandatory in ("plan_summary", "benefits", "coverage_exclusions"):
        if mandatory not in seen:
            unique_starts.append((len(lines), mandatory))

    unique_starts.sort(key=lambda t: t[0])

    sections: list[dict] = []
    for i, (start_idx, section_name) in enumerate(unique_starts):
        end_idx = unique_starts[i + 1][0] if i + 1 < len(unique_starts) else len(lines)
        section_lines = lines[start_idx:end_idx]
        raw_text = "\n".join(section_lines).strip()
        benefit_rows = _extract_benefit_rows(section_lines)
        sections.append(
            {
                "section_name": section_name,
                "benefit_rows": benefit_rows,
                "raw_text": raw_text,
            }
        )

    return sections


def _model_based_sections(
    pages: list[dict],
    model: AutoModelForTokenClassification,
    processor: LayoutLMv3Processor,
    device: torch.device,
) -> list[dict]:
    """Run LayoutLMv3 token classification to detect section boundaries."""
    id2label: dict[int, str] = model.config.id2label
    all_section_spans: dict[str, list[str]] = {s: [] for s in SECTION_LABELS}

    for page in pages:
        words = [w["text"] for w in page["words"]]
        if not words:
            logger.debug(
                f"[sbc_parser] page {page['page_num']}: no words from layout extractor, "
                "skipping model inference for this page"
            )
            continue

        word_boxes = [w["bbox"] for w in page["words"]]

        # LayoutLMv3 expects bboxes normalised to [0, 1000].  Approximate page
        # dimensions from the max coords seen on this page.
        max_x = max(b[2] for b in word_boxes) or 612  # US Letter fallback
        max_y = max(b[3] for b in word_boxes) or 792
        norm_boxes = [
            [
                int(b[0] * 1000 / max_x),
                int(b[1] * 1000 / max_y),
                int(b[2] * 1000 / max_x),
                int(b[3] * 1000 / max_y),
            ]
            for b in word_boxes
        ]

        try:
            tok_enc = processor.tokenizer(
                words,
                boxes=norm_boxes,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                is_split_into_words=True,
                padding="max_length",
            )
        except Exception as exc:
            logger.warning(f"[sbc_parser] tokenisation failed on page {page['page_num']}: {exc}")
            continue

        word_ids: list[int | None] = tok_enc.word_ids(batch_index=0)
        model_input = {k: v.to(device) for k, v in tok_enc.items()}

        with torch.no_grad():
            logits = model(**model_input).logits  # (1, seq_len, num_labels)

        pred_ids = logits[0].argmax(dim=-1).tolist()

        # Collapse sub-word tokens → first sub-token wins.
        word_label: dict[int, str] = {}
        for token_idx, w_id in enumerate(word_ids):
            if w_id is None or w_id in word_label:
                continue
            word_label[w_id] = id2label.get(pred_ids[token_idx], "O")

        # Accumulate word text per section span.
        current_section: str | None = None
        for w_id, word in enumerate(words):
            label = word_label.get(w_id, "O")
            if label.startswith("B-"):
                current_section = label[2:]
            elif label.startswith("I-"):
                pass  # continue current section
            else:
                current_section = None

            if current_section in all_section_spans:
                all_section_spans[current_section].append(word)

        logger.debug(
            f"[sbc_parser] page {page['page_num']}: model inference complete, "
            f"sections found: {[s for s, ws in all_section_spans.items() if ws]}"
        )

    # Convert accumulated word lists → section dicts.
    sections: list[dict] = []
    for section_name in SECTION_LABELS:
        section_words = all_section_spans[section_name]
        if not section_words:
            continue
        raw_text = " ".join(section_words)
        benefit_rows = _extract_benefit_rows(raw_text.splitlines())
        sections.append(
            {
                "section_name": section_name,
                "benefit_rows": benefit_rows,
                "raw_text": raw_text,
            }
        )

    # Guarantee mandatory sections are present even if the model missed them.
    present = {s["section_name"] for s in sections}
    for mandatory in ("plan_summary", "benefits", "coverage_exclusions"):
        if mandatory not in present:
            sections.append(
                {"section_name": mandatory, "benefit_rows": [], "raw_text": ""}
            )

    return sections


def _extract_benefit_rows(lines: list[str]) -> list[dict[str, str]]:
    """Extract structured benefit rows from a list of text lines.

    Each row looks like:
        ``{"service": "Primary care visit", "cost": "$30 copay"}``
    """
    rows: list[dict[str, str]] = []
    for line in lines:
        match = _BENEFIT_ROW_PATTERN.search(line)
        if match:
            rows.append(
                {
                    "service": match.group(1).strip(),
                    "cost": match.group(2).strip(),
                }
            )
    return rows


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class SBCParserRunner:
    """Parses a Summary of Benefits and Coverage (SBC) PDF into structured sections.

    When a trained LayoutLMv3 checkpoint is available it is used for section
    boundary detection.  When the checkpoint is absent the runner falls back to
    regex-based section detection so the pipeline remains functional during
    prototype development.
    """

    def __init__(self, model_dir: Path | None = None) -> None:
        checkpoint_dir = Path(model_dir) if model_dir else _DEFAULT_MODEL_DIR
        weights_path = checkpoint_dir / _WEIGHTS_FILENAME

        if checkpoint_dir.exists() and weights_path.exists():
            logger.info(f"[sbc_parser] loading model from {checkpoint_dir}")
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._processor = LayoutLMv3Processor.from_pretrained(
                str(checkpoint_dir), apply_ocr=False
            )
            self._model: AutoModelForTokenClassification | None = (
                AutoModelForTokenClassification.from_pretrained(
                    str(checkpoint_dir)
                ).to(self._device)
            )
            self._model.eval()
            logger.info("[sbc_parser] model loaded successfully")
        else:
            logger.warning(
                f"[sbc_parser] checkpoint not found at '{checkpoint_dir}'; "
                "falling back to rule-based section detection. "
                "Train with 'just train.sbc_parser' to enable ML-based parsing."
            )
            self._model = None
            self._processor = None
            self._device = torch.device("cpu")

    def __call__(self, pdf_path: str, document_id: str) -> dict[str, Any]:
        """Parse *pdf_path* and return structured SBC sections.

        Args:
            pdf_path: Absolute or relative path to the SBC PDF file.
            document_id: Opaque identifier echoed in the response.

        Returns:
            ``{document_id, sections: [{section_name, benefit_rows, raw_text}, ...]}``

        Raises:
            FileNotFoundError: If *pdf_path* does not exist.
            RuntimeError: If PDF text extraction fails entirely.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(
                f"SBC PDF not found at '{path}'. "
                "Ensure the file has been uploaded to 'data/raw/sbcs/'."
            )

        logger.info(f"[sbc_parser] parsing document_id={document_id!r}, file={path.name}")

        try:
            pages = _extract_pages(path)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to extract text from '{path.name}': {exc}"
            ) from exc

        total_chars = sum(len(p["text"]) for p in pages)
        logger.debug(
            f"[sbc_parser] extracted {len(pages)} pages, {total_chars} total chars"
        )

        if total_chars == 0:
            logger.warning(
                f"[sbc_parser] '{path.name}' yielded no extractable text; "
                "the PDF may be image-only — consider adding OCR support."
            )

        try:
            if self._model is not None and self._processor is not None:
                logger.debug("[sbc_parser] using model-based section detection")
                sections = _model_based_sections(
                    pages, self._model, self._processor, self._device
                )
            else:
                logger.debug("[sbc_parser] using rule-based section detection")
                sections = _rule_based_sections(pages)
        except Exception as exc:
            raise RuntimeError(
                f"Section detection failed for '{path.name}': {exc}"
            ) from exc

        logger.info(
            f"[sbc_parser] document_id={document_id!r} parsed: "
            f"{len(sections)} sections, "
            f"{sum(len(s['benefit_rows']) for s in sections)} benefit rows"
        )

        return {
            "document_id": document_id,
            "sections": sections,
        }
