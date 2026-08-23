from __future__ import annotations

from momo_fdvs.services.mtn_format_profile import load_bundled_mtn_profile
from momo_fdvs.services.passive_counterfeit import assess_passive_candidate
from momo_fdvs.services.sender_context import SenderContext

COUNTERFEIT = (
    "Cash In for Gh 700.00 from EXAMPLE TRADERS carent bulance.700.04 "
    "avelabil bulance.700.04 ID: 90000000000001 FEE: 00.000"
)
GENUINE = (
    "Cash In received for GHS 20.00 from SAMPLE SHOP. Current Balance GHS 80.00 "
    "Available Balance GHS 80.00. Transaction ID: 123456789. Fee charged: GHS 0. "
    "Cash in (Deposit) is a free transaction on MTN Mobile Money. Please do not pay "
    "any fees for it."
)


def test_counterfeit_candidate_emits_four_independent_evidence_codes() -> None:
    result = assess_passive_candidate(
        candidate_id="body-1",
        evidence_group_id="body-crop",
        region_kind="MESSAGE_BUBBLE",
        variant="GRAY",
        psm=6,
        raw_text=COUNTERFEIT,
        tokens=(
            {"text": "carent", "confidence": 94},
            {"text": "bulance", "confidence": 95},
            {"text": "avelabil", "confidence": 93},
        ),
        ocr_confidence=0.9,
        sender=SenderContext("phone_number", 0.95, True, False, "ocr_header"),
        format_profile=load_bundled_mtn_profile(),
    )

    assert set(result.evidence.reason_codes) == {
        "FINANCIAL_TERM_SPELLING_ANOMALY",
        "GENUINE_TEMPLATE_ANOMALY",
        "MALFORMED_FINANCIAL_FORMAT",
        "NUMERIC_SENDER_TRANSACTION_CLAIM",
    }
    assert result.format_anomalous is True


def test_genuine_candidate_under_provider_sender_has_no_passive_reason() -> None:
    result = assess_passive_candidate(
        candidate_id="body-1",
        evidence_group_id="body-crop",
        region_kind="MESSAGE_BUBBLE",
        variant="GRAY",
        psm=6,
        raw_text=GENUINE,
        tokens=(
            {"text": "Current", "confidence": 95},
            {"text": "Balance", "confidence": 95},
            {"text": "Available", "confidence": 95},
        ),
        ocr_confidence=0.9,
        sender=SenderContext("alphanumeric_provider", 0.95, False, True, "ocr_header"),
        format_profile=load_bundled_mtn_profile(),
    )

    assert result.evidence.reason_codes == ()
    assert result.format_anomalous is False


def test_profile_unavailable_omits_only_template_evidence() -> None:
    result = assess_passive_candidate(
        candidate_id="body-1",
        evidence_group_id="body-crop",
        region_kind="BODY",
        variant="HIGH_TEXT",
        psm=11,
        raw_text=COUNTERFEIT,
        tokens=(
            {"text": "carent", "confidence": 94},
            {"text": "bulance", "confidence": 95},
            {"text": "avelabil", "confidence": 93},
        ),
        ocr_confidence=0.9,
        sender=SenderContext("phone_number", 0.95, True, False, "ocr_header"),
        format_profile=None,
    )

    assert "GENUINE_TEMPLATE_ANOMALY" not in result.evidence.reason_codes
    assert "NUMERIC_SENDER_TRANSACTION_CLAIM" in result.evidence.reason_codes
    assert result.format_available is False
