from __future__ import annotations

import hashlib
import io
from typing import Any

import pytest
from flask import Flask
from PIL import Image, ImageDraw

from momo_fdvs.services import ocr
from momo_fdvs.services.ocr import (
    OCRCandidate,
    OCRFailure,
    create_preprocessing_variants,
    execute_ocr,
    normalize_amount,
    normalize_occurred_at,
    normalize_phone,
    normalize_reference,
    parse_fields,
)


def _receipt() -> bytes:
    image = Image.new("RGB", (900, 1200), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((60, 80, 840, 1120), outline="black", width=4)
    for index in range(10):
        draw.line((120, 180 + index * 75, 760, 180 + index * 75), fill="black", width=3)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _tokens(text: str, confidence: float = 92) -> list[dict[str, Any]]:
    return [
        {
            "id": index,
            "text": word,
            "confidence": confidence,
            "x": index * 20,
            "y": 10,
            "width": 18,
            "height": 12,
            "line_id": "1:1:1:1",
        }
        for index, word in enumerate(text.replace("\n", " ").split())
    ]


def test_normalizers_create_canonical_values() -> None:
    assert normalize_reference(" abc-123456 ") == "ABC-123456"
    assert normalize_reference("bad") is None
    assert normalize_amount("GH₵ 1,250.5") == "1250.50"
    assert normalize_amount("-1.00") is None
    assert normalize_phone("024 000 0001") == "+233240000001"
    assert normalize_phone("+233 24 000 0001") == "+233240000001"
    assert normalize_phone("123") is None
    occurred_at, warnings = normalize_occurred_at("08/08/2026 14:30")
    assert occurred_at == "2026-08-08T14:30:00Z"
    assert warnings == ["TIMEZONE_INFERRED_GHANA_UTC"]


def test_parser_extracts_controlled_fields_and_confidence() -> None:
    text = """MTN MOMO
TRANSACTION ID: ABC123456
AMOUNT: GHS 125.00
SENDER NAME: Demo Sender
SENDER PHONE: 0240000002
RECEIVER NAME: Demo Receiver
RECEIVER PHONE: 0240000001
DATE/TIME: 2026-08-08 14:30
STATUS: Successful"""
    fields, provider = parse_fields(text, _tokens(text), 0.75)
    assert provider["value"] == "MTN_MOMO"
    assert fields["transaction_reference"]["value"] == "ABC123456"
    assert fields["amount"]["value"] == "125.00"
    assert fields["currency"]["value"] == "GHS"
    assert fields["sender_name"]["value"] == "DEMO SENDER"
    assert fields["receiver_phone"]["value"] == "+233240000001"
    assert fields["occurred_at"]["value"] == "2026-08-08T14:30:00Z"
    assert fields["status_text"]["value"] == "SUCCESSFUL"
    assert not fields["amount"]["requires_review"]


def test_parser_flags_low_confidence_and_unknown_template() -> None:
    text = "TRANSACTION ID: ABC123456\nAMOUNT: GHS 12.00"
    fields, provider = parse_fields(text, _tokens(text, 45), 0.75)
    assert fields["transaction_reference"]["requires_review"]
    assert fields["occurred_at"]["warnings"] == ["FIELD_NOT_FOUND"]
    assert provider["value"] == "GENERIC_MOMO"
    assert "UNKNOWN_TEMPLATE_GENERIC_FALLBACK" in provider["warnings"]


def test_preprocessing_is_deterministic_and_does_not_change_original(app: Flask) -> None:
    content = _receipt()
    original_hash = hashlib.sha256(content).hexdigest()
    with app.app_context():
        first, quality = create_preprocessing_variants(content)
        second, _ = create_preprocessing_variants(content)
    assert set(first) >= {
        "BASE_RESIZED",
        "GRAY_CLAHE",
        "DENOISE_SHARPEN",
        "OTSU_BINARY",
        "ADAPTIVE_BINARY",
    }
    assert all((first[name] == second[name]).all() for name in first)
    assert quality["orientation_applied"] is True
    assert quality["opencv_version"]
    assert hashlib.sha256(content).hexdigest() == original_hash


def test_execute_ocr_returns_explicit_unavailable_state(
    app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = _receipt()
    monkeypatch.setattr(ocr.shutil, "which", lambda _command: None)
    with app.app_context():
        result = execute_ocr(content, hashlib.sha256(content).hexdigest())
    assert result.partial is True
    assert result.engine_version == "unavailable"
    assert "OCR_ENGINE_UNAVAILABLE" in result.warnings
    assert "CRITICAL_OCR_FIELDS_MISSING" in result.warnings
    assert result.selected_image.startswith(b"\x89PNG")


def test_execute_ocr_selects_coverage_not_only_mean_confidence(
    app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = _receipt()
    fields, provider = parse_fields("", [], 0.75)

    def fake_candidate(variant: str, _image: Any, psm: int, _threshold: float) -> OCRCandidate:
        coverage = 1.0 if variant == "GRAY_CLAHE" and psm == 6 else 0.0
        score = 0.91 if coverage else 0.70
        return OCRCandidate(
            variant,
            psm,
            "controlled",
            [],
            fields,
            provider,
            0.99 if not coverage else 0.80,
            0.99 if not coverage else 0.80,
            coverage,
            score,
        )

    monkeypatch.setattr(ocr.shutil, "which", lambda _command: "tesseract")
    monkeypatch.setattr(ocr.pytesseract, "get_tesseract_version", lambda: "5.3.0")
    monkeypatch.setattr(ocr, "_candidate", fake_candidate)
    with app.app_context():
        result = execute_ocr(content, hashlib.sha256(content).hexdigest())
    assert result.selected_variant == "GRAY_CLAHE"
    assert result.engine_version == "5.3.0"


def test_execute_ocr_rejects_evidence_hash_mismatch(app: Flask) -> None:
    with app.app_context(), pytest.raises(OCRFailure) as failure:
        execute_ocr(_receipt(), "0" * 64)
    assert failure.value.code == "OCR_RECEIPT_HASH_MISMATCH"
