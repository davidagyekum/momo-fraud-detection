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
    assert "+233" not in str(public)
    assert "5500" not in str(public)


def test_invalid_geometry_does_not_create_sender_evidence() -> None:
    result = infer_sender_context(
        [{"text": "+2335500...", "y": "invalid", "height": 20}],
        image_height=1280,
    )

    assert result.sender_kind == "unknown"
    assert result.source == "none"
