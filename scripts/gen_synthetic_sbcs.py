#!/usr/bin/env python3
"""Generate synthetic Summary of Benefits & Coverage (SBC) PDFs for dev/demo.

The real payor SBC URLs in data/ingest/configs/sbc_manifest.yaml rotate/expire
(most 404 or serve HTML), so this produces deterministic, valid PDFs (+ JSON
sidecars) under data/raw/sbcs/ so the SBC RAG pipeline (sbc_embed_ingest.py) has
realistic, offline content to index. Mirrors the repo's other synthetic-data
generators (synthetic_cards.py, generate_nppes_sample.py).

Usage:
    python scripts/gen_synthetic_sbcs.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from fpdf import FPDF
from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf

# Per-plan figure overrides. The demo plan mirrors its seeded structured benefits
# (PCP $30, urgent care $75, deductible $1,500, OOP $5,000, MRI 20% + prior auth,
# Humira Tier 4 + prior auth) so SBC passages stay consistent with the grounded facts.
OVERRIDES: dict[str, dict[str, str]] = {
    "ClaimVoice Demo PPO": {
        "deductible": "$1,500 individual",
        "oop_max": "$5,000 individual",
        "pcp": "$30 copay",
        "specialist": "$50 copay",
        "urgent": "$75 copay",
        "er": "$250 copay",
        "imaging": "20% coinsurance after deductible and requires prior authorization",
        "rx": "Tier 1 generic drugs are a $10 copay; Tier 4 specialty drugs such as "
              "Humira require prior authorization before coverage applies",
    },
}
DEFAULT: dict[str, str] = {
    "deductible": "$3,500 individual",
    "oop_max": "$8,500 individual",
    "pcp": "$35 copay",
    "specialist": "$70 copay",
    "urgent": "$90 copay",
    "er": "$400 copay",
    "imaging": "30% coinsurance after deductible and requires prior authorization",
    "rx": "Tier 1 generic drugs are a $15 copay; specialty drugs require prior authorization",
}


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def build_text(name: str, f: dict[str, str]) -> str:
    """Multi-section SBC-style body referencing the plan name and its figures."""
    return "\n".join([
        f"Summary of Benefits and Coverage: {name}",
        "Coverage Period: 01/01/2026 - 12/31/2026",
        "",
        "PLAN SUMMARY",
        f"This Summary of Benefits and Coverage (SBC) describes what the {name} plan "
        "covers and what you pay for covered services. It is only a summary; the plan "
        "policy and contract govern in all cases.",
        "",
        "IMPORTANT QUESTIONS",
        f"What is the overall deductible? The annual deductible is {f['deductible']}. "
        "You must generally meet the deductible before the plan begins to pay for most "
        "services, except for in-network preventive care which is covered at no cost.",
        f"What is the out-of-pocket limit for this plan? The out-of-pocket maximum is "
        f"{f['oop_max']}. After you reach this amount the plan pays 100% of the allowed "
        "amount for covered, in-network services for the rest of the plan year.",
        "",
        "COMMON MEDICAL EVENTS AND YOUR COST",
        f"Primary care visit to treat an injury or illness: {f['pcp']} in network.",
        f"Specialist visit: {f['specialist']} in network. A referral may be required.",
        f"Urgent care: {f['urgent']} in network for after-hours and walk-in care.",
        f"Emergency room care: {f['er']}; the copay is waived if you are admitted.",
        f"Diagnostic imaging (CT, PET, and MRI scans): {f['imaging']}. An MRI is a "
        "covered benefit but the ordering provider must obtain prior authorization "
        "from the plan before the scan is performed, or the claim may be denied.",
        "Hospital stay (facility fee): 20% coinsurance after deductible, prior "
        "authorization required for non-emergency admissions.",
        "",
        "PRESCRIPTION DRUG COVERAGE",
        f"The plan uses a four-tier formulary. {f['rx']}. Step therapy and quantity "
        "limits may apply to selected medications.",
        "",
        "EXCLUDED SERVICES",
        "Services the plan does NOT cover include: cosmetic surgery, long-term care, "
        "routine foot care, weight-loss programs, dental care for adults, and most "
        "care received outside the United States.",
        "",
        "YOUR RIGHTS",
        "You have the right to appeal a denied claim and to request a copy of the full "
        "plan document. Coverage examples are illustrative and not a cost estimate.",
    ])


def write_pdf(path: Path, name: str, body: str) -> None:
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    width = pdf.epw  # effective page width (page width minus left/right margins)
    for line in body.split("\n"):
        if not line:
            pdf.ln(4)
            continue
        pdf.multi_cell(width, 6, line)
    pdf.output(str(path))


def main() -> None:
    config_dir = Path(__file__).resolve().parent.parent / "data" / "ingest" / "configs"
    with initialize_config_dir(version_base=None, config_dir=str(config_dir)):
        cfg = compose(config_name="sbc_manifest", overrides=sys.argv[1:])

    out_dir = Path(cfg.sbcs.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for entry in cfg.sbcs.plans:
        name = entry["plan_name"]
        payor = entry["payor"]
        figures = OVERRIDES.get(name, DEFAULT)
        filename = f"{payor}_{_slugify(name)}.pdf"
        pdf_path = out_dir / filename
        write_pdf(pdf_path, name, build_text(name, figures))
        (pdf_path.with_suffix(".json")).write_text(json.dumps({
            "url": "synthetic",
            "payor": payor,
            "plan_name": name,
            "plan_year": entry["plan_year"],
        }, indent=2))
        print(f"wrote {filename}  -> {name}")
        count += 1

    print(f"done: {count} synthetic SBC PDFs in {out_dir}")


if __name__ == "__main__":
    main()
