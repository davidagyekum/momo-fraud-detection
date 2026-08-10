#!/usr/bin/env python3
"""Measure OCR required-field extraction on deterministic controlled receipts."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from flask import Flask
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from momo_fdvs.services.ocr import REQUIRED_FIELDS, execute_ocr

SEED = 20260810
EXPECTED = {
    "transaction_reference": "ABC123456",
    "amount": "125.00",
    "currency": "GHS",
    "occurred_at": "2026-08-08T14:30:00Z",
}


@dataclass(frozen=True)
class FixtureResult:
    fixture: str
    status: str
    selected_variant: str
    warnings: list[str]
    expected_fields: int
    matched_fields: int
    field_matches: dict[str, bool]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _base_receipt() -> Image.Image:
    image = Image.new("RGB", (1400, 1800), "white")
    draw = ImageDraw.Draw(image)
    title = _font(54)
    body = _font(42)
    draw.rounded_rectangle((70, 60, 1330, 1730), radius=24, outline="black", width=4)
    draw.text((140, 130), "MOBILE MONEY RECEIPT", fill="black", font=title)
    lines = (
        "MTN MOMO",
        "TRANSACTION ID: ABC123456",
        "AMOUNT: GHS 125.00",
        "SENDER NAME: DEMO SENDER",
        "SENDER PHONE: 0240000002",
        "RECEIVER NAME: DEMO RECEIVER",
        "RECEIVER PHONE: 0240000001",
        "DATE/TIME: 2026-08-08 14:30",
        "STATUS: SUCCESSFUL",
    )
    for index, line in enumerate(lines):
        draw.text((140, 280 + index * 135), line, fill="black", font=body)
    return image


def _png(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def controlled_fixtures() -> dict[str, bytes]:
    base = _base_receipt()
    rotated = base.rotate(4, resample=Image.Resampling.BICUBIC, fillcolor="white")
    low_contrast = ImageEnhance.Contrast(base).enhance(0.35)
    rng = np.random.default_rng(SEED)
    array = np.asarray(base).astype(np.int16)
    noise = rng.normal(0, 12, array.shape).astype(np.int16)
    noisy = Image.fromarray(np.clip(array + noise, 0, 255).astype(np.uint8))
    cropped = base.crop((90, 90, 1310, 1530))
    return {
        "clean": _png(base),
        "rotated_4deg": _png(rotated),
        "low_contrast": _png(low_contrast),
        "noisy": _png(noisy),
        "cropped": _png(cropped),
    }


def _app() -> Flask:
    app = Flask(__name__)
    app.config.update(
        TESSERACT_CMD="tesseract",
        TESSERACT_LANG="eng",
        TESSERACT_TIMEOUT_SECONDS=20,
        OCR_REVIEW_CONFIDENCE_THRESHOLD=0.75,
        OCR_MAX_VARIANTS=6,
        OCR_TARGET_MIN_WIDTH_PX=1200,
    )
    return app


def evaluate() -> dict[str, Any]:
    fixture_results: list[FixtureResult] = []
    per_field = Counter({name: 0 for name in REQUIRED_FIELDS})
    total_expected = 0
    total_matched = 0
    app = _app()
    with app.app_context():
        for name, content in controlled_fixtures().items():
            result = execute_ocr(content, hashlib.sha256(content).hexdigest())
            matches = {
                field: result.fields[field]["value"] == expected
                for field, expected in EXPECTED.items()
            }
            matched = sum(matches.values())
            total_expected += len(matches)
            total_matched += matched
            per_field.update(field for field, is_match in matches.items() if is_match)
            fixture_results.append(
                FixtureResult(
                    fixture=name,
                    status="PARTIAL" if result.partial else "COMPLETE",
                    selected_variant=result.selected_variant,
                    warnings=result.warnings,
                    expected_fields=len(matches),
                    matched_fields=matched,
                    field_matches=matches,
                )
            )
    count = len(fixture_results)
    return {
        "evaluation_scope": "controlled synthetic generic Ghana-style receipts only",
        "seed": SEED,
        "engine": "Tesseract",
        "fixture_count": count,
        "required_field_matches": total_matched,
        "required_field_expected": total_expected,
        "required_field_accuracy": round(total_matched / total_expected, 4),
        "per_field_accuracy": {
            field: round(per_field[field] / count, 4) for field in REQUIRED_FIELDS
        },
        "fixtures": [asdict(result) for result in fixture_results],
        "limitations": [
            "Controlled synthetic text is not representative of real provider receipts.",
            "This report is OCR extraction evidence, not fraud-model performance.",
            "No production accuracy or provider-wide generalisation is claimed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    print(json.dumps(evaluate(), indent=None if args.compact else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
