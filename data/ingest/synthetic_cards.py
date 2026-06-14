#!/usr/bin/env python3
"""
Synthetic Insurance Card Generator: Produce 100 PNG training images for LayoutLMv3 OCR.

Generates 4 payor templates × 25 cards = 100 PNGs using Pillow + Faker.
Each card is CR80 size (1012×638 px at 300 dpi). All member data is synthetic.
Writes data/processed/synthetic_cards/card_NNNN.png and labels.jsonl.

labels.jsonl format (one JSON object per line):
  {"file": "card_0001.png", "payor": "aetna", "fields": {
    "member_id":    {"text": "W123456789", "bbox": [x1, y1, x2, y2]},
    "first_name":   {"text": "Jane",       "bbox": [...]},
    ...
  }}
  bbox coordinates are pixel-absolute (not normalized).

Usage:
    python data/ingest/synthetic_cards.py
    python data/ingest/synthetic_cards.py --output-dir data/processed/synthetic_cards
"""

import argparse
import json
import logging
import math
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from faker import Faker
from PIL import Image, ImageDraw, ImageFilter, ImageFont

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# CR80 card dimensions at 300 dpi
CARD_W = 1012
CARD_H = 638
CARDS_PER_PAYOR = 25
OUTPUT_DIR = Path("data/processed/synthetic_cards")

# Faker seeds per payor — fixed for reproducibility
_FAKER_SEEDS = {"aetna": 1001, "uhc": 2002, "bcbs": 3003, "cigna": 4004}

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class BBox:
    x1: int
    y1: int
    x2: int
    y2: int

    def to_list(self) -> list[int]:
        return [self.x1, self.y1, self.x2, self.y2]


@dataclass
class FieldSpec:
    """Where and how to render a single field on the card."""
    label: str           # label text printed above the value
    x: int               # top-left x of the value text area
    y: int               # top-left y of the value text area
    font_size: int = 22
    label_font_size: int = 16
    max_width: Optional[int] = None


@dataclass
class PayorTemplate:
    name: str
    bg_color: tuple        # RGB card background
    accent_color: tuple    # RGB for header band
    text_color: tuple      # RGB for value text
    label_color: tuple     # RGB for field labels
    header_text: str       # insurer name in header
    header_height: int     # px height of top header band
    fields: list[FieldSpec] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Payor templates
# ---------------------------------------------------------------------------

def _aetna_template() -> PayorTemplate:
    return PayorTemplate(
        name="aetna",
        bg_color=(248, 248, 252),
        accent_color=(126, 0, 47),       # Aetna deep red
        text_color=(30, 30, 30),
        label_color=(100, 100, 110),
        header_text="AETNA",
        header_height=90,
        fields=[
            FieldSpec("Member ID",   50,  130, font_size=28, max_width=280),
            FieldSpec("Member Name", 50,  210, font_size=24, max_width=340),
            FieldSpec("Date of Birth", 50, 290, font_size=22),
            FieldSpec("Group Number", 440, 130, font_size=24, max_width=260),
            FieldSpec("Plan Name",   440, 210, font_size=20, max_width=320),
            FieldSpec("Effective Date", 440, 290, font_size=22),
            FieldSpec("RxBIN",       50,  390, font_size=22),
            FieldSpec("RxPCN",       250, 390, font_size=22),
            FieldSpec("Phone",       50,  470, font_size=20),
        ],
    )


def _uhc_template() -> PayorTemplate:
    return PayorTemplate(
        name="uhc",
        bg_color=(240, 247, 255),
        accent_color=(0, 61, 130),        # UHC navy
        text_color=(20, 20, 50),
        label_color=(80, 100, 130),
        header_text="UnitedHealthcare",
        header_height=85,
        fields=[
            FieldSpec("Member ID",   60,  125, font_size=28, max_width=290),
            FieldSpec("Name",        60,  205, font_size=24, max_width=350),
            FieldSpec("DOB",         60,  285, font_size=22),
            FieldSpec("Group #",     460, 125, font_size=24, max_width=250),
            FieldSpec("Plan",        460, 205, font_size=20, max_width=310),
            FieldSpec("Eff. Date",   460, 285, font_size=22),
            FieldSpec("RxBIN",       60,  385, font_size=22),
            FieldSpec("RxPCN",       260, 385, font_size=22),
            FieldSpec("Phone",       60,  465, font_size=20),
        ],
    )


def _bcbs_template() -> PayorTemplate:
    return PayorTemplate(
        name="bcbs",
        bg_color=(245, 250, 255),
        accent_color=(0, 102, 179),       # BCBS blue
        text_color=(15, 15, 40),
        label_color=(70, 110, 160),
        header_text="BlueCross BlueShield",
        header_height=95,
        fields=[
            FieldSpec("Member ID",   55,  140, font_size=28, max_width=285),
            FieldSpec("Subscriber",  55,  220, font_size=24, max_width=345),
            FieldSpec("Birth Date",  55,  300, font_size=22),
            FieldSpec("Group",       450, 140, font_size=24, max_width=255),
            FieldSpec("Plan Name",   450, 220, font_size=20, max_width=315),
            FieldSpec("Eff. Date",   450, 300, font_size=22),
            FieldSpec("RxBIN",       55,  400, font_size=22),
            FieldSpec("RxPCN",       255, 400, font_size=22),
            FieldSpec("Customer Svc", 55, 475, font_size=20),
        ],
    )


def _cigna_template() -> PayorTemplate:
    return PayorTemplate(
        name="cigna",
        bg_color=(250, 248, 245),
        accent_color=(0, 150, 140),       # Cigna teal
        text_color=(25, 25, 25),
        label_color=(90, 110, 105),
        header_text="Cigna",
        header_height=88,
        fields=[
            FieldSpec("ID Number",   58,  133, font_size=28, max_width=287),
            FieldSpec("Member",      58,  213, font_size=24, max_width=348),
            FieldSpec("DOB",         58,  293, font_size=22),
            FieldSpec("Group No.",   455, 133, font_size=24, max_width=258),
            FieldSpec("Plan",        455, 213, font_size=20, max_width=318),
            FieldSpec("Effective",   455, 293, font_size=22),
            FieldSpec("RxBIN",       58,  393, font_size=22),
            FieldSpec("RxPCN",       258, 393, font_size=22),
            FieldSpec("Phone",       58,  468, font_size=20),
        ],
    )


TEMPLATES = [_aetna_template(), _uhc_template(), _bcbs_template(), _cigna_template()]


# ---------------------------------------------------------------------------
# Member data generation
# ---------------------------------------------------------------------------

_PLAN_NAMES = {
    "aetna": ["Aetna Bronze 6850", "Aetna Silver 3500", "Aetna Gold 1500"],
    "uhc":   ["UHC Choice Plus Bronze", "UHC Navigate Silver", "UHC Gold Plus"],
    "bcbs":  ["BCBS Blue Value Bronze", "BCBS Blue Select Silver", "BCBS Blue Focus Gold"],
    "cigna": ["Cigna Connect 5700", "Cigna True Choice Silver", "Cigna LocalPlus Gold"],
}

_RX_BINS = {"aetna": "610191", "uhc": "610011", "bcbs": "610014", "cigna": "610585"}
_RX_PCNS = {"aetna": "AETCVS", "uhc": "UHEALTH", "bcbs": "ADV", "cigna": "CIGNA"}
_PHONES  = {
    "aetna": "1-800-US-AETNA",
    "uhc":   "1-866-801-4409",
    "bcbs":  "1-800-810-2583",
    "cigna": "1-800-244-6224",
}


def _generate_member(fake: Faker, payor: str, card_num: int) -> dict:
    random.seed(card_num * 17 + _FAKER_SEEDS[payor])
    fake.seed_instance(card_num * 17 + _FAKER_SEEDS[payor])

    member_id = payor[0].upper() + fake.numerify("?????????")
    dob = fake.date_of_birth(minimum_age=18, maximum_age=75)
    plan_name = random.choice(_PLAN_NAMES[payor])
    eff_year = 2026
    eff_date = f"01/01/{eff_year}"
    group_num = fake.bothify("??####??").upper()

    return {
        "member_id":     member_id,
        "first_name":    fake.first_name(),
        "last_name":     fake.last_name(),
        "dob":           dob.strftime("%m/%d/%Y"),
        "group_number":  group_num,
        "plan_name":     plan_name,
        "rx_bin":        _RX_BINS[payor],
        "rx_pcn":        _RX_PCNS[payor],
        "effective_date": eff_date,
        "phone":         _PHONES[payor],
    }


# ---------------------------------------------------------------------------
# Card rendering
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.ImageFont:
    """Load a default Pillow font at a given size, falling back to built-in."""
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except OSError:
            return ImageFont.load_default()


def _text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple:
    """Return (width, height) of rendered text."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _truncate_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: Optional[int],
) -> str:
    if max_width is None:
        return text
    while text and _text_bbox(draw, text, font)[0] > max_width:
        text = text[:-1]
    return text.rstrip()


def _field_values(member: dict, spec: FieldSpec) -> str:
    """Map a FieldSpec label to the corresponding member data value."""
    label_lower = spec.label.lower()
    if "member id" in label_lower or "id number" in label_lower:
        return member["member_id"]
    if "name" in label_lower or "member" in label_lower or "subscriber" in label_lower:
        return f"{member['first_name']} {member['last_name']}"
    if "birth" in label_lower or "dob" in label_lower:
        return member["dob"]
    if "group" in label_lower:
        return member["group_number"]
    if "plan" in label_lower:
        return member["plan_name"]
    if "eff" in label_lower or "effective" in label_lower:
        return member["effective_date"]
    if "rxbin" in label_lower or "rxbin" in label_lower.replace(" ", ""):
        return member["rx_bin"]
    if "rxpcn" in label_lower or "rxpcn" in label_lower.replace(" ", ""):
        return member["rx_pcn"]
    if "phone" in label_lower or "svc" in label_lower:
        return member["phone"]
    return ""


def _render_card(
    template: PayorTemplate,
    member: dict,
    rng: random.Random,
) -> tuple[Image.Image, dict]:
    """
    Render one insurance card image and return (image, fields_dict).
    fields_dict maps field_key → {"text": str, "bbox": [x1, y1, x2, y2]}.
    """
    img = Image.new("RGB", (CARD_W, CARD_H), template.bg_color)
    draw = ImageDraw.Draw(img)

    # Header band
    draw.rectangle([(0, 0), (CARD_W, template.header_height)], fill=template.accent_color)
    header_font = _load_font(36)
    draw.text((30, (template.header_height - 40) // 2), template.header_text,
              fill=(255, 255, 255), font=header_font)

    # Bottom accent strip
    draw.rectangle([(0, CARD_H - 18), (CARD_W, CARD_H)], fill=template.accent_color)

    # Thin separator line below header
    draw.line([(0, template.header_height), (CARD_W, template.header_height)],
              fill=template.accent_color, width=2)

    fields_out: dict = {}

    # Render each field
    for spec in template.fields:
        label_font = _load_font(spec.label_font_size)
        value_font = _load_font(spec.font_size)

        # Label
        lx, ly = spec.x, spec.y
        draw.text((lx, ly), spec.label.upper(), fill=template.label_color, font=label_font)
        _, lh = _text_bbox(draw, spec.label.upper(), label_font)

        # Value
        raw_value = _field_values(member, spec)
        value = _truncate_text(draw, raw_value, value_font, spec.max_width)
        vx, vy = lx, ly + lh + 4
        draw.text((vx, vy), value, fill=template.text_color, font=value_font)
        vw, vh = _text_bbox(draw, value, value_font)

        bbox = BBox(x1=vx, y1=vy, x2=vx + vw, y2=vy + vh)
        field_key = spec.label.lower().replace(" ", "_").replace(".", "").replace("#", "num")
        fields_out[field_key] = {"text": raw_value, "bbox": bbox.to_list()}

    return img, fields_out


def _augment(img: Image.Image, rng: random.Random) -> Image.Image:
    """Apply mild augmentations: slight rotation, brightness jitter, soft blur."""
    # Rotation ±5°
    angle = rng.uniform(-5.0, 5.0)
    img = img.rotate(angle, resample=Image.BICUBIC, expand=False,
                     fillcolor=(230, 230, 230))

    # Brightness jitter via point transform (±10% intensity)
    factor = rng.uniform(0.90, 1.10)
    img = img.point(lambda p: max(0, min(255, int(p * factor))))

    # Very slight blur to simulate real photo/scan
    if rng.random() < 0.4:
        img = img.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.3, 0.8)))

    # JPEG compression artifact simulation: save to bytes at lower quality then reload
    import io
    quality = rng.randint(72, 95)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    img = Image.open(buf).copy()

    return img


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def generate_cards(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    labels_path = output_dir / "labels.jsonl"

    fake = Faker("en_US")
    card_num = 0
    label_lines: list[str] = []

    for template in TEMPLATES:
        payor_rng = random.Random(_FAKER_SEEDS[template.name])
        logger.info("Generating %d cards for payor: %s", CARDS_PER_PAYOR, template.name)

        for i in range(CARDS_PER_PAYOR):
            card_num += 1
            member = _generate_member(fake, template.name, i)
            aug_rng = random.Random(_FAKER_SEEDS[template.name] + i)

            img, fields = _render_card(template, member, payor_rng)
            img = _augment(img, aug_rng)

            filename = f"card_{card_num:04d}.png"
            img.save(output_dir / filename, format="PNG")

            record = {
                "file":   filename,
                "payor":  template.name,
                "fields": fields,
            }
            label_lines.append(json.dumps(record))

    labels_path.write_text("\n".join(label_lines) + "\n", encoding="utf-8")

    logger.info(
        "synthetic_cards complete: %d PNGs + labels.jsonl written to %s",
        card_num,
        output_dir,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic insurance card images")
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="Output directory for PNGs and labels.jsonl",
    )
    args = parser.parse_args()
    generate_cards(Path(args.output_dir))


if __name__ == "__main__":
    main()
