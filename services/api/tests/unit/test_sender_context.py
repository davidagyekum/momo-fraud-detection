from __future__ import annotations

from typing import Any

from momo_fdvs.services.sender_context import infer_sender_context


def _token(
    text: str,
    y: int,
    x: int = 100,
    confidence: float = 95.0,
) -> dict[str, Any]:
    return {
        "text": text,
        "x": x,
        "y": y,
        "width": 160,
        "height": 35,
        "confidence": confidence,
        "line_id": f"line-{y}",
    }


def test_truncated_ghana_number_in_header_is_numeric_sender() -> None:
    result = infer_sender_context(
        [_token("+2335470...", 60), _token("Cash", 650), _token("700.00", 650, 260)],
        image_height=1280,
    )

    assert result.sender_kind == "phone_number"
    assert result.header_phone_present is True
    assert result.sender_confidence >= 0.8


def test_spaced_ghana_number_subsequence_in_noisy_header_is_numeric_sender() -> None:
    result = infer_sender_context(
        [
            _token("<", 55, 20, 15.0),
            _token("+233", 55, 90, 92.0),
            _token("55", 55, 215, 88.0),
            _token("436", 55, 285, 84.0),
            _token("9301", 55, 385, 80.0),
            _token("phone", 55, 570, 25.0),
            _token("video", 55, 690, 30.0),
            _token("⋮", 55, 830, 10.0),
            _token("Cash", 650, 100),
        ],
        image_height=1280,
    )

    assert result.sender_kind == "phone_number"
    assert result.header_phone_present is True
    assert result.header_provider_label_present is False
    assert result.source == "ocr_header"
    assert result.sender_confidence >= 0.72


def test_spaced_ghana_number_subsequence_in_body_is_not_numeric_sender() -> None:
    result = infer_sender_context(
        [
            _token("Messages", 55, 100, 94.0),
            _token("+233", 700, 90, 92.0),
            _token("55", 700, 215, 88.0),
            _token("436", 700, 285, 84.0),
            _token("9301", 700, 385, 80.0),
        ],
        image_height=1280,
    )

    assert result.sender_kind == "unknown"
    assert result.header_phone_present is False
    assert result.header_provider_label_present is False
    assert result.source == "none"


def test_header_transaction_id_that_looks_like_233_number_is_not_sender() -> None:
    result = infer_sender_context(
        [
            _token("Transaction", 55, 80, 96.0),
            _token("ID:", 55, 270, 96.0),
            _token("233", 55, 350, 93.0),
            _token("55", 55, 450, 91.0),
            _token("436", 55, 520, 89.0),
            _token("9301", 55, 620, 87.0),
        ],
        image_height=1280,
    )

    assert result.sender_kind == "unknown"
    assert result.header_phone_present is False
    assert result.source == "none"


def test_mobilemoney_header_is_provider_label() -> None:
    result = infer_sender_context(
        [_token("MobileMoney", 55), _token("Payment", 600)],
        image_height=1280,
    )

    assert result.sender_kind == "alphanumeric_provider"
    assert result.header_provider_label_present is True


def test_body_phone_is_not_used_as_sender() -> None:
    result = infer_sender_context(
        [_token("MobileMoney", 55), _token("0244000000", 800)],
        image_height=1280,
    )

    assert result.sender_kind == "alphanumeric_provider"
    assert result.header_phone_present is False


def test_header_fallback_uses_first_raw_lines_without_exposing_value() -> None:
    result = infer_sender_context(
        [],
        image_height=1280,
        raw_text="+2335500...\nCash In for Gh 5",
    )
    public = result.as_public_dict()

    assert result.sender_kind == "phone_number"
    assert result.sender_confidence == 0.55
    assert result.source == "raw_text_fallback"
    assert result.header_phone_present is False
    assert result.header_provider_label_present is False
    assert "+233" not in str(public)
    assert "5500" not in str(public)


def test_invalid_geometry_does_not_create_sender_evidence() -> None:
    result = infer_sender_context(
        [{"text": "+2335500...", "y": "invalid", "height": 20}],
        image_height=1280,
    )

    assert result.sender_kind == "unknown"
    assert result.source == "none"
