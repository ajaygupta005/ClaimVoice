#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
uv run python -m models.card_ocr_layoutlm.evaluate
uv run python -m models.payor_classifier_resnet.evaluate
uv run python -m models.sbc_parser_layoutlm.evaluate
