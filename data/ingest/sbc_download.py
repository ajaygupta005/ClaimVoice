#!/usr/bin/env python3
"""
SBC PDF Downloader: Fetch Summary of Benefits and Coverage PDFs from payor websites.

Reads a manifest of known PDF URLs from configs/sbc_manifest.yaml, downloads each
file to data/raw/sbcs/<payor>_<plan_slug>.pdf with exponential-backoff retry,
and writes a JSON sidecar alongside each PDF.

Usage:
    python data/ingest/sbc_download.py
    python data/ingest/sbc_download.py sbcs.output_dir=data/raw/sbcs
"""

import json
import logging
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0  # seconds; retry delays: 2s, 4s, 8s


def _slugify(text: str) -> str:
    """Convert plan name to a filesystem-safe slug."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _download_with_retry(url: str, dest: Path) -> int:
    """
    Download url to dest with exponential-backoff retry.
    Returns file size in bytes.
    Raises on all retries exhausted.
    """
    last_exc: Exception = RuntimeError("no attempts made")
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            logger.info("Downloading (attempt %d/%d): %s", attempt, _MAX_RETRIES, url)
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ClaimVoice-SBC-Fetcher/1.0"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            dest.write_bytes(data)
            return len(data)
        except (urllib.error.URLError, OSError) as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                delay = _BACKOFF_BASE ** attempt
                logger.warning("Attempt %d failed (%s); retrying in %.0fs", attempt, exc, delay)
                time.sleep(delay)
    raise RuntimeError(f"Failed after {_MAX_RETRIES} attempts: {last_exc}") from last_exc


def _write_sidecar(pdf_path: Path, entry: dict, file_size_bytes: int) -> None:
    """Write a JSON metadata sidecar alongside the PDF."""
    sidecar = {
        "url": entry["url"],
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "payor": entry["payor"],
        "plan_name": entry["plan_name"],
        "plan_year": entry["plan_year"],
        "file_size_bytes": file_size_bytes,
    }
    sidecar_path = pdf_path.with_suffix(".json")
    sidecar_path.write_text(json.dumps(sidecar, indent=2))
    logger.info("Wrote sidecar: %s", sidecar_path.name)


def download_sbcs(cfg) -> None:
    out_dir = Path(cfg.sbcs.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    plans = cfg.sbcs.plans
    total = len(plans)
    downloaded = skipped = failed = 0

    for entry in plans:
        payor = entry["payor"]
        plan_name = entry["plan_name"]
        plan_year = entry["plan_year"]
        url = entry["url"]

        filename = f"{payor}_{_slugify(plan_name)}.pdf"
        pdf_path = out_dir / filename

        if pdf_path.exists():
            logger.info("Already exists, skipping: %s", filename)
            skipped += 1
            continue

        try:
            size = _download_with_retry(url, pdf_path)
            _write_sidecar(pdf_path, dict(entry), size)
            logger.info("Saved %s (%.1f KB)", filename, size / 1024)
            downloaded += 1
        except Exception as exc:
            logger.error("FAILED %s: %s", url, exc)
            failed += 1

    logger.info(
        "sbc_download complete: total=%d downloaded=%d skipped=%d failed=%d",
        total, downloaded, skipped, failed,
    )
    if failed:
        logger.warning(
            "%d PDF(s) failed — update URLs in configs/sbc_manifest.yaml and re-run",
            failed,
        )


def main() -> None:
    config_dir = Path(__file__).parent / "configs"
    with initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = compose(config_name="sbc_manifest", overrides=sys.argv[1:])

    logger.info("Config:\n%s", OmegaConf.to_yaml(cfg))
    download_sbcs(cfg)


if __name__ == "__main__":
    main()
