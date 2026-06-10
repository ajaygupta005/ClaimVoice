#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
uv run python -m models.payor_classifier_resnet.train
