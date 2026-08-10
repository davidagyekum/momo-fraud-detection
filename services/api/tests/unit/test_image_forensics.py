from __future__ import annotations

import hashlib

import numpy as np
from PIL import Image

from momo_fdvs.services.image_forensics import (
    _compression_evidence,
    _layout_evidence,
    _metadata_evidence,
    _noise_evidence,
)


def _manipulated_image() -> tuple[Image.Image, np.ndarray]:
    values = np.full((320, 240, 3), 238, dtype=np.uint8)
    values[40:280:20, 20:220] = 30
    rng = np.random.default_rng(20260810)
    values[160:, 120:] = rng.integers(0, 256, size=(160, 120, 3), dtype=np.uint8)
    return Image.fromarray(values, mode="RGB"), values


def test_metadata_absence_is_neutral_and_encoder_hint_is_contextual(app) -> None:
    receipt = type(
        "ReceiptEvidence",
        (),
        {"media_type": "image/png", "width_px": 240, "height_px": 320},
    )()
    with app.app_context():
        neutral = _metadata_evidence(
            receipt,
            {
                "decoded_format": "PNG",
                "decoded_mode": "RGB",
                "decoded_width_px": 240,
                "decoded_height_px": 320,
                "exif_present": False,
                "software_encoder": None,
            },
        )
        hinted = _metadata_evidence(
            receipt,
            {
                "decoded_format": "PNG",
                "decoded_mode": "RGB",
                "decoded_width_px": 240,
                "decoded_height_px": 320,
                "exif_present": True,
                "software_encoder": "Adobe Photoshop controlled",
            },
        )
    absent = next(signal for signal in neutral["signals"] if signal["code"] == "METADATA_ABSENT")
    assert absent["status"] == "NEUTRAL"
    assert absent["severity"] == "INFORMATIONAL"
    editing = next(
        signal for signal in hinted["signals"] if signal["code"] == "EDITING_SOFTWARE_HINT"
    )
    assert editing["status"] == "TRIGGERED"
    assert editing["severity"] == "LOW"
    assert "supporting evidence only" in editing["reason"]


def test_recompression_and_noise_features_are_deterministic(app) -> None:
    image, values = _manipulated_image()
    with app.app_context():
        app.config["IMAGE_FORENSICS_ELA_REGIONAL_CV_THRESHOLD"] = 0.01
        app.config["IMAGE_FORENSICS_NOISE_REGIONAL_CV_THRESHOLD"] = 0.01
        first_compression = _compression_evidence(image)
        second_compression = _compression_evidence(image)
        first_noise = _noise_evidence(values, None)
        second_noise = _noise_evidence(values, None)
    assert first_compression[0] == second_compression[0]
    assert first_compression[1] == second_compression[1]
    assert (
        hashlib.sha256(first_compression[2] or b"").digest()
        == hashlib.sha256(second_compression[2] or b"").digest()
    )
    assert first_compression[0]["signals"][0]["status"] == "TRIGGERED"
    assert first_noise[0] == second_noise[0]
    assert first_noise[1] == second_noise[1]
    assert first_noise[0]["signals"][0]["status"] == "TRIGGERED"
    assert first_noise[2] is not None and second_noise[2] is not None


def test_tiny_images_return_not_applicable_instead_of_invented_values(app) -> None:
    image = Image.new("RGB", (64, 64), "white")
    values = np.asarray(image, dtype=np.uint8)
    with app.app_context():
        compression, compression_features, ela = _compression_evidence(image)
        noise, noise_features, noise_map = _noise_evidence(values, None)
    assert compression["signals"][0]["status"] == "NOT_APPLICABLE"
    assert compression_features == {} and ela is None
    assert noise["signals"][0]["status"] == "NOT_APPLICABLE"
    assert noise_features == {} and noise_map is None


def test_ocr_layout_records_alignment_crop_and_missing_token_states(app) -> None:
    tokens = [
        {"x": 1, "y": 10, "width": 40, "height": 12, "line_id": "line-1"},
        {"x": 45, "y": 35, "width": 40, "height": 30, "line_id": "line-1"},
        {"x": 20, "y": 25, "width": 80, "height": 12, "line_id": "line-2"},
    ]
    with app.app_context():
        app.config["IMAGE_FORENSICS_BASELINE_THRESHOLD"] = 0.05
        app.config["IMAGE_FORENSICS_HEIGHT_CV_THRESHOLD"] = 0.05
        evidence, features = _layout_evidence(tokens, 240, 320)
        unavailable, unavailable_features = _layout_evidence([], 240, 320)
    statuses = {signal["code"]: signal["status"] for signal in evidence["signals"]}
    assert statuses["TEXT_ALIGNMENT_INCONSISTENCY"] == "TRIGGERED"
    assert statuses["POSSIBLE_CROP_OR_EDGE_INCOMPLETENESS"] == "TRIGGERED"
    assert features["layout_overlap_count"] >= 1
    assert unavailable["signals"][0]["status"] == "NOT_APPLICABLE"
    assert unavailable_features == {}
