from __future__ import annotations

import cv2
import numpy as np
import pytest
from tests.fixtures.generated_passive_counterfeit import (
    generated_passive_counterfeit_png,
)

from momo_fdvs.services import ocr
from momo_fdvs.services.ocr import FraudOcrCandidate
from momo_fdvs.services.ocr_regions import discover_ocr_regions


def _fixture_bgr() -> np.ndarray:
    encoded = np.frombuffer(generated_passive_counterfeit_png(), dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    assert image is not None
    return image


def _candidate(region_kind: str, variant: str, psm: int) -> FraudOcrCandidate:
    return FraudOcrCandidate(
        candidate_id=f"{region_kind}:{variant}:{psm}",
        evidence_group_id=f"{region_kind}:controlled-crop",
        region_kind=region_kind,
        variant=variant,
        psm=psm,
        raw_text="controlled",
        tokens=(),
        mean_confidence=0.9,
    )


def test_synthetic_gray_message_bubble_is_discovered() -> None:
    regions = discover_ocr_regions(_fixture_bgr())
    kinds = [region.kind for region in regions]

    assert kinds[:3] == ["FULL_IMAGE", "HEADER", "BODY"]
    assert "MESSAGE_BUBBLE" in kinds
    assert kinds.count("MESSAGE_BUBBLE") <= 3


def test_region_public_summaries_do_not_expose_coordinates() -> None:
    regions = discover_ocr_regions(_fixture_bgr())

    for region in regions:
        public = region.as_public_dict()
        assert set(public) == {"kind", "score_band"}
        assert not {"x", "y", "width", "height", "bbox"} & set(public)


def test_region_discovery_rejects_invalid_images() -> None:
    with pytest.raises(ValueError):
        discover_ocr_regions(np.zeros((20, 20), dtype=np.uint8))


def test_fraud_candidate_count_is_capped(app, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ocr,
        "_fraud_candidate",
        lambda region, variant_name, _image, psm, _timeout: _candidate(
            region.kind, variant_name, psm
        ),
    )

    with app.app_context():
        candidates, warnings = ocr._build_fraud_candidates(_fixture_bgr(), timeout_seconds=20)

    assert 0 < len(candidates) <= 32
    assert warnings == []


def test_one_region_failure_leaves_other_fraud_candidates_usable(
    app, monkeypatch: pytest.MonkeyPatch
) -> None:
    def candidate(region, variant_name, _image, psm, _timeout):
        if region.kind == "HEADER":
            raise RuntimeError("controlled region timeout")
        return _candidate(region.kind, variant_name, psm)

    monkeypatch.setattr(ocr, "_fraud_candidate", candidate)

    with app.app_context():
        candidates, warnings = ocr._build_fraud_candidates(_fixture_bgr(), timeout_seconds=20)

    assert candidates
    assert any(item.region_kind == "BODY" for item in candidates)
    assert "OCR_FRAUD_CANDIDATE_TIMEOUT" in warnings
