#!/usr/bin/env python3
"""
Generate synthetic insurance card PNG images + labels.jsonl for LayoutLMv3 training.

Each card has three visual zones:
  - Header (top 130 px)   : carrier name, plan name, plan-type badge
  - Info   (next 190 px)  : member name/DOB/effective-date, member-id, group number
  - RX     (bottom 105 px): Rx BIN / PCN / Group, customer-service phone

Output files
  data/processed/synthetic_cards/<id>.png
  data/processed/synthetic_cards/labels.jsonl

labels.jsonl format (one JSON object per line):
  {
    "id": str,
    "image_path": str,
    "payor_class": str,
    "width": 675, "height": 425,
    "fields": { field_name: value, ... },
    "words": [str, ...],         # whitespace-split tokens
    "boxes": [[x0,y0,x1,y1],...],# normalised to [0, 1000]
    "ner_tags": [str, ...]        # "O" | "B-<field>" | "I-<field>"
  }

Usage:
    python data/ingest/synthetic_cards.py
    python data/ingest/synthetic_cards.py --count 50 --seed 42
    python data/ingest/synthetic_cards.py --count 5 --out /tmp/cards
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path

from faker import Faker
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

CARD_W, CARD_H = 675, 425       # standard insurance-card size at 200 DPI

HEADER_H = 130                  # y: 0   – 130
INFO_H   = 190                  # y: 130 – 320
RX_H     = 105                  # y: 320 – 425

INFO_Y = HEADER_H               # 130
RX_Y   = HEADER_H + INFO_H      # 320

COL_LEFT  = 24                  # left column x anchor
COL_RIGHT = 345                 # right column x anchor
COL_RX2   = 252
COL_RX3   = 476

WHITE        = (255, 255, 255)
LABEL_COLOR  = (100, 100, 110)  # small caps field labels (gray)
VALUE_COLOR  = (18,  18,  24)   # field values (near-black)
DIVIDER_COLOR = (205, 210, 220)

PAYOR_CLASSES = ["Aetna", "UHC", "Cigna", "BCBS", "Humana", "Kaiser", "Anthem", "Other"]

# ---------------------------------------------------------------------------
# Payor visual configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PayorConfig:
    header_bg:  tuple   # RGB fill for header zone
    rx_bg:      tuple   # RGB fill for RX zone
    rx_fg:      tuple   # RGB text color in RX zone
    plan_names: tuple   # pool of plan names to sample


PAYOR_CONFIGS: dict[str, PayorConfig] = {
    "Aetna": PayorConfig(
        header_bg=(125, 34, 72),
        rx_bg=(250, 240, 244),
        rx_fg=(100, 20, 50),
        plan_names=("Aetna Choice POS II", "Aetna PPO", "Aetna HMO Select"),
    ),
    "UHC": PayorConfig(
        header_bg=(0, 38, 119),
        rx_bg=(235, 240, 252),
        rx_fg=(0, 38, 119),
        plan_names=("UHC Choice Plus PPO", "UHC Navigate HMO", "UHC Options PPO"),
    ),
    "Cigna": PayorConfig(
        header_bg=(0, 55, 119),
        rx_bg=(235, 242, 252),
        rx_fg=(0, 55, 119),
        plan_names=("Cigna Open Access Plus", "Cigna LocalPlus", "Cigna SureFit PPO"),
    ),
    "BCBS": PayorConfig(
        header_bg=(0, 48, 135),
        rx_bg=(240, 243, 252),
        rx_fg=(0, 48, 135),
        plan_names=("BlueCross PPO Select", "BlueShield HMO", "BCBS Blue Options PPO"),
    ),
    "Humana": PayorConfig(
        header_bg=(0, 122, 51),
        rx_bg=(235, 250, 241),
        rx_fg=(0, 90, 38),
        plan_names=("Humana HMO", "Humana Choice PPO", "Humana Gold Plus HMO"),
    ),
    "Kaiser": PayorConfig(
        header_bg=(0, 100, 177),
        rx_bg=(235, 244, 252),
        rx_fg=(0, 70, 130),
        plan_names=("Kaiser HMO", "Kaiser Permanente HMO", "KP Deductible HMO"),
    ),
    "Anthem": PayorConfig(
        header_bg=(0, 56, 101),
        rx_bg=(235, 241, 248),
        rx_fg=(0, 40, 80),
        plan_names=("Anthem EPO", "Anthem Blue Access PPO", "Anthem HMO Classic"),
    ),
    "Other": PayorConfig(
        header_bg=(68, 68, 78),
        rx_bg=(245, 245, 246),
        rx_fg=(50, 50, 58),
        plan_names=("National Health PPO", "Community HMO", "Allied Health EPO"),
    ),
}

# ---------------------------------------------------------------------------
# Font loading (with graceful cross-platform fallback)
# ---------------------------------------------------------------------------

_FONT_CACHE: dict[tuple, ImageFont.FreeTypeFont] = {}

# (path, ttc_index) — tried in order, first success wins
_REGULAR_FONT_CANDIDATES = [
    ("/System/Library/Fonts/SFNS.ttf",          0),
    ("/System/Library/Fonts/HelveticaNeue.ttc",  0),
    ("/System/Library/Fonts/Helvetica.ttc",      0),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",           0),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 0),
]
_BOLD_FONT_CANDIDATES = [
    ("/System/Library/Fonts/ArialHB.ttc",        0),
    ("/System/Library/Fonts/HelveticaNeue.ttc",  4),
    ("/System/Library/Fonts/Helvetica.ttc",      1),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",      0),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 0),
    # safe fallback — same as regular if nothing else loads
    ("/System/Library/Fonts/SFNS.ttf",           0),
]


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    candidates = _BOLD_FONT_CANDIDATES if bold else _REGULAR_FONT_CANDIDATES
    for path, idx in candidates:
        try:
            f = ImageFont.truetype(path, size, index=idx)
            _FONT_CACHE[key] = f
            return f
        except (OSError, IOError):
            continue
    # Pillow 10+ built-in bitmap font — always available
    try:
        f = ImageFont.load_default(size=size)
    except TypeError:
        f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f

# ---------------------------------------------------------------------------
# Synthetic field value generators
# ---------------------------------------------------------------------------


def _member_id() -> str:
    prefix = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=3))
    digits = "".join(random.choices("0123456789", k=9))
    return prefix + digits


def _group_number() -> str:
    pfx = random.choice(["GRP", "GR", "G", ""])
    digits = "".join(random.choices("0123456789", k=random.randint(4, 8)))
    return pfx + digits


def _rx_bin() -> str:
    return "".join(random.choices("0123456789", k=6))


def _rx_pcn() -> str:
    return "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789",
                                  k=random.randint(4, 8)))


def _rx_group() -> str:
    return "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789",
                                  k=random.randint(3, 7)))


def _effective_date() -> str:
    year  = random.choice([2023, 2024, 2025, 2026])
    month = random.choice([1, 7])       # typical plan-year starts
    return f"{month:02d}/01/{year}"


def _customer_phone() -> str:
    area   = random.randint(200, 999)
    prefix = random.randint(200, 999)
    line   = random.randint(1000, 9999)
    return f"1-{area}-{prefix}-{line}"


def _plan_type_from_name(plan_name: str) -> str:
    for pt in ("PPO", "HMO", "EPO", "POS", "HDHP"):
        if pt in plan_name.upper():
            return pt
    return random.choice(("PPO", "HMO"))

# ---------------------------------------------------------------------------
# Bbox normalisation helper
# ---------------------------------------------------------------------------


def _norm_box(bbox: tuple) -> list[int]:
    """Convert a Pillow textbbox tuple (x0,y0,x1,y1) → LayoutLMv3 [0,1000] range."""
    x0, y0, x1, y1 = bbox
    return [
        max(0, min(1000, round(x0 * 1000 / CARD_W))),
        max(0, min(1000, round(y0 * 1000 / CARD_H))),
        max(0, min(1000, round(x1 * 1000 / CARD_W))),
        max(0, min(1000, round(y1 * 1000 / CARD_H))),
    ]

# ---------------------------------------------------------------------------
# Word drawing + tracking (core primitive)
# ---------------------------------------------------------------------------


def _put_token(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    token: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple,
    tag: str,
    words: list,
    boxes: list,
    tags: list,
) -> int:
    """Draw *token* at (x, y), record its bbox and NER tag. Returns right edge x."""
    bb = draw.textbbox((x, y), token, font=font)
    draw.text((x, y), token, font=font, fill=fill)
    words.append(token)
    boxes.append(_norm_box(bb))
    tags.append(tag)
    return bb[2]  # right edge (x1)


def _draw_text_row(
    draw: ImageDraw.ImageDraw,
    x_start: int,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple,
    field_name: str,           # "O" → label word, else BIO-tagged field
    words: list,
    boxes: list,
    tags: list,
    gap: int = 4,
) -> int:
    """Draw whitespace-split tokens left-to-right. Returns right edge of last token."""
    tokens = text.split()
    x = x_start
    for i, tok in enumerate(tokens):
        if field_name == "O":
            tag = "O"
        elif i == 0:
            tag = f"B-{field_name}"
        else:
            tag = f"I-{field_name}"
        x = _put_token(draw, x, y, tok, font, fill, tag, words, boxes, tags)
        x += gap
    return x


def _draw_field(
    draw: ImageDraw.ImageDraw,
    x: int,
    y_label: int,
    y_value: int,
    label_text: str,
    value_text: str,
    field_name: str,
    words: list,
    boxes: list,
    tags: list,
) -> None:
    """Draw a (label, value) pair stacked vertically, recording every word."""
    # small-caps label — tagged O
    _draw_text_row(draw, x, y_label, label_text, _font(9),      LABEL_COLOR, "O",         words, boxes, tags, gap=3)
    # field value — tagged B-/I-<field_name>
    _draw_text_row(draw, x, y_value, value_text, _font(13, bold=True), VALUE_COLOR, field_name, words, boxes, tags)

# ---------------------------------------------------------------------------
# Card renderer
# ---------------------------------------------------------------------------


def generate_card(
    payor_class: str,
    fake: Faker,
    cfg: PayorConfig,
) -> tuple[Image.Image, dict]:
    """Render one synthetic insurance card.

    Returns:
        (PIL Image, label_dict) where label_dict contains fields, words, boxes, ner_tags.
    """
    img  = Image.new("RGB", (CARD_W, CARD_H), WHITE)
    draw = ImageDraw.Draw(img)

    words: list[str]      = []
    boxes: list[list[int]] = []
    tags:  list[str]      = []

    # ── Header zone ──────────────────────────────────────────────────────────
    draw.rectangle([(0, 0), (CARD_W, HEADER_H)], fill=cfg.header_bg)

    carrier_name = (
        payor_class
        if payor_class != "Other"
        else fake.company().split()[0] + " Health"
    )
    plan_name = random.choice(cfg.plan_names)
    plan_type = _plan_type_from_name(plan_name)

    # Carrier name — large bold white text
    _draw_text_row(draw, COL_LEFT, 22, carrier_name, _font(22, bold=True),
                   WHITE, "carrier", words, boxes, tags, gap=6)

    # Plan name — medium white text below carrier
    _draw_text_row(draw, COL_LEFT, 58, plan_name, _font(13),
                   WHITE, "plan_name", words, boxes, tags, gap=4)

    # Plan-type badge — top-right corner
    badge_w, badge_h = 66, 26
    bx0 = CARD_W - badge_w - 14
    by0 = 14
    bx1, by1 = bx0 + badge_w, by0 + badge_h
    try:
        draw.rounded_rectangle([(bx0, by0), (bx1, by1)], radius=5, fill=WHITE)
    except AttributeError:                          # Pillow < 8.2
        draw.rectangle([(bx0, by0), (bx1, by1)], fill=WHITE)
    f_badge = _font(11, bold=True)
    bb_pt   = draw.textbbox((0, 0), plan_type, font=f_badge)
    tw, th  = bb_pt[2] - bb_pt[0], bb_pt[3] - bb_pt[1]
    btx     = bx0 + (badge_w - tw) // 2
    bty     = by0 + (badge_h - th) // 2
    draw.text((btx, bty), plan_type, font=f_badge, fill=cfg.header_bg)
    actual_bb = draw.textbbox((btx, bty), plan_type, font=f_badge)
    words.append(plan_type)
    boxes.append(_norm_box(actual_bb))
    tags.append("B-plan_type")

    # ── Info zone ─────────────────────────────────────────────────────────────
    draw.rectangle([(0, INFO_Y), (CARD_W, INFO_Y + INFO_H)], fill=WHITE)
    draw.line([(0, INFO_Y), (CARD_W, INFO_Y)], fill=DIVIDER_COLOR, width=2)

    member_name = fake.name()
    dob_val     = fake.date_of_birth(minimum_age=18, maximum_age=80).strftime("%m/%d/%Y")
    eff_date    = _effective_date()
    mid_val     = _member_id()
    grp_val     = _group_number()

    # Left column
    _draw_field(draw, COL_LEFT,  INFO_Y + 16,  INFO_Y + 30,  "MEMBER NAME",    member_name, "name",           words, boxes, tags)
    _draw_field(draw, COL_LEFT,  INFO_Y + 70,  INFO_Y + 84,  "DATE OF BIRTH",  dob_val,     "dob",            words, boxes, tags)
    _draw_field(draw, COL_LEFT,  INFO_Y + 124, INFO_Y + 138, "EFFECTIVE DATE", eff_date,    "effective_date", words, boxes, tags)

    # Right column
    _draw_field(draw, COL_RIGHT, INFO_Y + 16,  INFO_Y + 30,  "MEMBER ID",      mid_val,     "member_id",      words, boxes, tags)
    _draw_field(draw, COL_RIGHT, INFO_Y + 70,  INFO_Y + 84,  "GROUP NUMBER",   grp_val,     "group_number",   words, boxes, tags)

    # Divider above RX zone
    draw.line([(14, INFO_Y + INFO_H - 3), (CARD_W - 14, INFO_Y + INFO_H - 3)],
              fill=DIVIDER_COLOR, width=1)

    # ── RX zone ───────────────────────────────────────────────────────────────
    draw.rectangle([(0, RX_Y), (CARD_W, CARD_H)], fill=cfg.rx_bg)
    draw.line([(0, RX_Y), (CARD_W, RX_Y)], fill=DIVIDER_COLOR, width=1)

    rxb_val   = _rx_bin()
    rxp_val   = _rx_pcn()
    rxg_val   = _rx_group()
    phone_val = _customer_phone()

    rx_label_y = RX_Y + 10
    rx_value_y = RX_Y + 24

    _draw_field(draw, COL_LEFT, rx_label_y, rx_value_y, "Rx BIN",   rxb_val, "rx_bin",   words, boxes, tags)
    _draw_field(draw, COL_RX2,  rx_label_y, rx_value_y, "Rx PCN",   rxp_val, "rx_pcn",   words, boxes, tags)
    _draw_field(draw, COL_RX3,  rx_label_y, rx_value_y, "Rx Group", rxg_val, "rx_group", words, boxes, tags)

    # Phone — draw the value centred on the card
    ph_f    = _font(13, bold=True)
    ph_bb0  = draw.textbbox((0, 0), phone_val, font=ph_f)
    ph_w    = ph_bb0[2] - ph_bb0[0]
    ph_vx   = (CARD_W - ph_w) // 2
    ph_vy   = RX_Y + 68

    # "CUSTOMER SERVICE" label centred above the value
    lf      = _font(9)
    lbl_bb0 = draw.textbbox((0, 0), "CUSTOMER SERVICE", font=lf)
    lbl_w   = lbl_bb0[2] - lbl_bb0[0]
    lbl_x   = (CARD_W - lbl_w) // 2
    lbl_y   = RX_Y + 54
    _draw_text_row(draw, lbl_x, lbl_y, "CUSTOMER SERVICE", lf, LABEL_COLOR, "O", words, boxes, tags, gap=3)
    _draw_text_row(draw, ph_vx, ph_vy,  phone_val, ph_f,  cfg.rx_fg, "phone", words, boxes, tags)

    # ── Assemble metadata ─────────────────────────────────────────────────────
    label_record = {
        "payor_class": payor_class,
        "width":  CARD_W,
        "height": CARD_H,
        "fields": {
            "carrier":        carrier_name,
            "plan_name":      plan_name,
            "plan_type":      plan_type,
            "name":           member_name,
            "dob":            dob_val,
            "effective_date": eff_date,
            "member_id":      mid_val,
            "group_number":   grp_val,
            "rx_bin":         rxb_val,
            "rx_pcn":         rxp_val,
            "rx_group":       rxg_val,
            "phone":          phone_val,
        },
        "words":    words,
        "boxes":    boxes,
        "ner_tags": tags,
    }
    return img, label_record

# ---------------------------------------------------------------------------
# Dataset generation loop
# ---------------------------------------------------------------------------


def run(count: int, seed: int, out_dir: Path) -> None:
    random.seed(seed)
    Faker.seed(seed)
    fake = Faker()

    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "labels.jsonl"

    total = 0
    with jsonl_path.open("w") as jf:
        for payor_class in PAYOR_CLASSES:
            cfg = PAYOR_CONFIGS[payor_class]
            for i in range(1, count + 1):
                card_id  = f"{payor_class.lower()}_{i:04d}"
                img, lbl = generate_card(payor_class, fake, cfg)

                img_filename = f"{card_id}.png"
                img.save(out_dir / img_filename, format="PNG")

                record = {"id": card_id, "image_path": img_filename, **lbl}
                jf.write(json.dumps(record) + "\n")

                total += 1
                if i % 10 == 0 or i == count:
                    print(f"  {payor_class:8s}: {i:>{len(str(count))}}/{count}", flush=True)

    print(f"\nGenerated {total} cards  →  {out_dir}")
    print(f"Labels    {total} rows   →  {jsonl_path}")

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate synthetic insurance card images for LayoutLMv3 training."
    )
    p.add_argument("--count", type=int, default=20,
                   help="Cards per payor class (default: 20 → 160 total)")
    p.add_argument("--seed",  type=int, default=42,
                   help="Random seed for reproducibility (default: 42)")
    p.add_argument("--out",   type=str, default=None,
                   help="Output directory (default: data/processed/synthetic_cards/)")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    repo_root = Path(__file__).parents[2]
    out_dir   = Path(args.out) if args.out else repo_root / "data" / "processed" / "synthetic_cards"

    n_total = args.count * len(PAYOR_CLASSES)
    print(f"Generating {args.count} cards × {len(PAYOR_CLASSES)} payors = {n_total} total")
    print(f"Seed: {args.seed}   Output: {out_dir}\n")
    run(args.count, args.seed, out_dir)


if __name__ == "__main__":
    main()
