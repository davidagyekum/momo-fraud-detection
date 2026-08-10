from __future__ import annotations

import io

import pytest
from flask import Flask
from PIL import Image

from momo_fdvs.services.receipts import ReceiptFailure, inspect_receipt, validate_client_metadata


def image_bytes(image_format: str = "PNG", *, size: tuple[int, int] = (640, 480)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, (240, 240, 240)).save(output, format=image_format)
    return output.getvalue()


@pytest.mark.parametrize(
    ("image_format", "filename", "media_type"),
    [
        ("JPEG", "receipt.jpg", "image/jpeg"),
        ("PNG", "receipt.png", "image/png"),
        ("WEBP", "receipt.webp", "image/webp"),
    ],
)
def test_valid_image_is_hashed_and_thumbnail_is_derived(
    app: Flask, image_format: str, filename: str, media_type: str
) -> None:
    content = image_bytes(image_format)
    with app.app_context():
        inspected = inspect_receipt(content, f"folder/{filename}")

    assert inspected.content == content
    assert inspected.display_filename == filename
    assert inspected.media_type == media_type
    assert inspected.width_px == 640
    assert inspected.height_px == 480
    assert len(inspected.sha256) == 64
    assert len(inspected.perceptual_hash) == 16
    assert inspected.thumbnail.startswith(b"\xff\xd8")


@pytest.mark.parametrize(
    ("content", "filename", "code"),
    [
        (b"MZ" + b"not-an-image", "receipt.png", "INVALID_RECEIPT_CONTENT"),
        (b"%PDF-1.7", "receipt.png", "INVALID_RECEIPT_CONTENT"),
        (b"<svg></svg>", "receipt.png", "INVALID_RECEIPT_CONTENT"),
        (image_bytes("PNG"), "receipt.jpg", "RECEIPT_EXTENSION_MISMATCH"),
        (
            image_bytes("PNG") + b"<script>payload</script>",
            "receipt.png",
            "INVALID_RECEIPT_CONTENT",
        ),
        (
            image_bytes("JPEG") + b"second-image\xff\xd9",
            "receipt.jpg",
            "INVALID_RECEIPT_CONTENT",
        ),
    ],
)
def test_rejects_disguised_mismatched_and_polyglot_files(
    app: Flask, content: bytes, filename: str, code: str
) -> None:
    with app.app_context(), pytest.raises(ReceiptFailure) as raised:
        inspect_receipt(content, filename)
    assert raised.value.code == code


def test_rejects_oversized_and_excessive_dimensions(app: Flask) -> None:
    with app.app_context():
        app.config["UPLOAD_MAX_BYTES"] = 10
        with pytest.raises(ReceiptFailure) as oversized:
            inspect_receipt(image_bytes(), "receipt.png")
        assert oversized.value.status == 413

        app.config["UPLOAD_MAX_BYTES"] = 10_485_760
        app.config["UPLOAD_MAX_PIXEL_COUNT"] = 1_000
        with pytest.raises(ReceiptFailure) as pixels:
            inspect_receipt(image_bytes(size=(100, 100)), "receipt.png")
        assert pixels.value.code == "RECEIPT_PIXEL_LIMIT_EXCEEDED"


def test_rejects_animation_and_unsafe_metadata(app: Flask) -> None:
    animated = io.BytesIO()
    frames = [Image.new("RGB", (320, 320), color) for color in ("white", "black")]
    frames[0].save(animated, format="WEBP", save_all=True, append_images=frames[1:], duration=50)
    with app.app_context():
        with pytest.raises(ReceiptFailure) as raised:
            inspect_receipt(animated.getvalue(), "receipt.webp")
        assert raised.value.code == "ANIMATED_RECEIPT_NOT_ALLOWED"
        with pytest.raises(ReceiptFailure, match="scalar"):
            validate_client_metadata('{"nested":{"not":"allowed"}}')
