from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from momo_fdvs.services.hybrid_text_risk import (
    HYBRID_RULESET_VERSION,
    HYBRID_SCHEMA_VERSION,
    assess_hybrid_ocr,
    finalize_hybrid_assessment,
    stored_hybrid_assessment_projection,
)
from momo_fdvs.services.mtn_format_profile import MtnFormatProfileError
from momo_fdvs.services.ocr_evidence_consensus import ConsensusEvidence
from momo_fdvs.services.sender_context import SenderContext
from momo_fdvs.services.text_fraud import stored_text_assessment_projection


def _consensus(*codes: str) -> ConsensusEvidence:
    return ConsensusEvidence(
        tuple(sorted(codes)),
        {code: 2 for code in codes},
        {code: 0.9 for code in codes},
        4,
        (),
    )


def test_numeric_sender_plus_template_anomaly_is_fraudulent() -> None:
    result = finalize_hybrid_assessment(
        _consensus("NUMERIC_SENDER_TRANSACTION_CLAIM", "GENUINE_TEMPLATE_ANOMALY"),
        evidence_quality="HIGH",
        sender=SenderContext("phone_number", 0.95, True, False, "ocr_header"),
    )

    assert result.risk_class == "FRAUDULENT"
    assert result.risk_score is not None and result.risk_score >= 90
    assert result.score_is_probability is False
    assert result.ruleset_version == HYBRID_RULESET_VERSION
    assert result.as_public_dict()["summary"] == "Likely counterfeit transaction notification"


def test_spelling_alone_is_inconclusive() -> None:
    result = finalize_hybrid_assessment(
        _consensus("FINANCIAL_TERM_SPELLING_ANOMALY"),
        evidence_quality="HIGH",
    )

    assert result.risk_class is None
    assert result.risk_score is None


def test_two_medium_anomaly_families_are_suspicious_not_fraudulent() -> None:
    result = finalize_hybrid_assessment(
        _consensus("FINANCIAL_TERM_SPELLING_ANOMALY", "MALFORMED_FINANCIAL_FORMAT"),
        evidence_quality="HIGH",
    )

    assert result.risk_class == "SUSPICIOUS"
    assert result.risk_score == 56


def test_low_quality_single_format_anomaly_is_not_fraudulent() -> None:
    result = finalize_hybrid_assessment(
        _consensus("GENUINE_TEMPLATE_ANOMALY"),
        evidence_quality="LOW",
    )

    assert result.risk_class == "SUSPICIOUS"
    assert result.risk_score is not None and result.risk_score < 90


def test_profile_integrity_failure_cannot_create_a_counterfeit_verdict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_profile_load() -> None:
        raise MtnFormatProfileError("PROFILE_INTEGRITY_FAILURE", "controlled failure")

    monkeypatch.setattr(
        "momo_fdvs.services.hybrid_text_risk.load_bundled_mtn_profile",
        fail_profile_load,
    )
    candidate = SimpleNamespace(
        candidate_id="BODY:GRAY:6",
        region_kind="BODY",
        variant="GRAY",
        psm=6,
        raw_text="Cash In received for GHS 10.00 from SAMPLE SHOP.",
        tokens=({"text": "Cash", "confidence": 95, "y": 600, "height": 30},),
        mean_confidence=0.9,
    )
    second_candidate = SimpleNamespace(
        **{
            **vars(candidate),
            "candidate_id": "MESSAGE_BUBBLE:GRAY:11",
            "region_kind": "MESSAGE_BUBBLE",
            "psm": 11,
        }
    )

    result = assess_hybrid_ocr(
        selected_raw_text="+2335500...",
        selected_tokens=(
            {
                "text": "+2335500...",
                "confidence": 95,
                "x": 100,
                "y": 55,
                "width": 240,
                "height": 40,
                "line_id": "header",
            },
        ),
        provider_code="GENERIC_MOMO",
        fraud_candidates=(candidate, second_candidate),
        image_height=1280,
    )

    assert result.risk_class == "SUSPICIOUS"
    assert result.profile_status == "UNAVAILABLE"
    assert "MTN_FORMAT_PROFILE_INTEGRITY_FAILURE" in result.limitations


def test_existing_pin_request_remains_decisive_without_regional_candidates() -> None:
    result = assess_hybrid_ocr(
        selected_raw_text="Send your MoMo PIN and OTP now for verification.",
        selected_tokens=({"text": "OTP", "confidence": 95, "y": 500, "height": 30},),
        provider_code="MTN_MOMO",
        fraud_candidates=(),
        image_height=1280,
    )

    assert result.risk_class == "FRAUDULENT"
    assert "PIN_OR_OTP_REQUEST" in result.reason_codes
    assert result.as_public_dict()["summary"] == "Strong scam indicators detected"


def test_raw_text_sender_fallback_cannot_become_numeric_header_evidence() -> None:
    candidate = SimpleNamespace(
        candidate_id="BODY:GRAY:6",
        region_kind="BODY",
        variant="GRAY",
        psm=6,
        raw_text="Cash In received for GHS 10.00 from SAMPLE SHOP.",
        tokens=({"text": "Cash", "confidence": 95, "y": 700, "height": 30},),
        mean_confidence=0.9,
    )

    result = assess_hybrid_ocr(
        selected_raw_text="+2335500...\nCash In received for GHS 10.00",
        selected_tokens=(),
        provider_code="TELECEL_CASH",
        fraud_candidates=(candidate,),
        image_height=1280,
    )

    assert result.sender.source == "raw_text_fallback"
    assert result.sender.sender_confidence == 0.55
    assert result.sender.header_phone_present is False
    assert "NUMERIC_SENDER_TRANSACTION_CLAIM" not in result.reason_codes
    projection = stored_hybrid_assessment_projection(result.as_public_dict())
    assert projection["evidence"]["sender"]["source"] == "raw_text_fallback"


def test_controlled_candidate_family_produces_four_reasons_and_high_risk() -> None:
    raw = (
        "Cash In for Gh 700.00 from EXAMPLE TRADERS carent bulance.700.04 "
        "avelabil bulance.700.04 ID: 90000000000001 FEE: 00.000"
    )
    candidate = SimpleNamespace(
        candidate_id="BODY:HIGH_TEXT:6",
        region_kind="BODY",
        variant="HIGH_TEXT",
        psm=6,
        raw_text=raw,
        tokens=(
            {"text": "carent", "confidence": 94, "y": 650, "height": 30},
            {"text": "bulance", "confidence": 95, "y": 650, "height": 30},
            {"text": "avelabil", "confidence": 93, "y": 700, "height": 30},
        ),
        mean_confidence=0.9,
    )
    second_candidate = SimpleNamespace(
        **{
            **vars(candidate),
            "candidate_id": "MESSAGE_BUBBLE:GRAY:11",
            "region_kind": "MESSAGE_BUBBLE",
            "variant": "GRAY",
            "psm": 11,
        }
    )
    result = assess_hybrid_ocr(
        selected_raw_text="+2335500...",
        selected_tokens=(
            {
                "text": "+2335500...",
                "confidence": 95,
                "x": 100,
                "y": 55,
                "width": 240,
                "height": 40,
                "line_id": "header",
            },
        ),
        provider_code="GENERIC_MOMO",
        fraud_candidates=(candidate, second_candidate),
        image_height=1280,
    )

    assert result.risk_class == "FRAUDULENT"
    assert set(result.reason_codes) == {
        "FINANCIAL_TERM_SPELLING_ANOMALY",
        "GENUINE_TEMPLATE_ANOMALY",
        "MALFORMED_FINANCIAL_FORMAT",
        "NUMERIC_SENDER_TRANSACTION_CLAIM",
    }


@pytest.mark.parametrize("provider_code", ["TELECEL_CASH", "AIRTELTIGO_MONEY"])
def test_explicit_non_mtn_provider_never_uses_mtn_format_profile(
    provider_code: str,
) -> None:
    candidate = SimpleNamespace(
        candidate_id="BODY:HIGH_TEXT:6",
        region_kind="BODY",
        variant="HIGH_TEXT",
        psm=6,
        raw_text=(
            "Cash In for Gh 700.00 from EXAMPLE TRADERS carent bulance.700.04 "
            "avelabil bulance.700.04 ID: 90000000000001 FEE: 00.000"
        ),
        tokens=(
            {"text": "carent", "confidence": 94, "y": 650, "height": 30},
            {"text": "bulance", "confidence": 95, "y": 650, "height": 30},
            {"text": "avelabil", "confidence": 93, "y": 700, "height": 30},
        ),
        mean_confidence=0.9,
    )

    result = assess_hybrid_ocr(
        selected_raw_text="+2335500...",
        selected_tokens=(
            {
                "text": "+2335500...",
                "confidence": 95,
                "x": 100,
                "y": 55,
                "width": 240,
                "height": 40,
                "line_id": "header",
            },
        ),
        provider_code=provider_code,
        fraud_candidates=(candidate,),
        image_height=1280,
    )

    assert "GENUINE_TEMPLATE_ANOMALY" not in result.reason_codes
    assert result.profile_status == "NOT_APPLICABLE"
    projection = stored_hybrid_assessment_projection(result.as_public_dict())
    assert projection["evidence"]["format_profile"]["status"] == "NOT_APPLICABLE"


@pytest.mark.parametrize("provider_label", ["Telecel Cash", "AirtelTigo Money"])
def test_generic_provider_with_conflicting_label_never_uses_mtn_profile(
    provider_label: str,
) -> None:
    candidate = SimpleNamespace(
        candidate_id="BODY:HIGH_TEXT:6",
        region_kind="BODY",
        variant="HIGH_TEXT",
        psm=6,
        raw_text=(
            f"{provider_label} Cash In for Gh 700.00 from EXAMPLE TRADERS "
            "carent bulance.700.04 avelabil bulance.700.04 ID: 90000000000001"
        ),
        tokens=({"text": provider_label, "confidence": 94, "y": 650, "height": 30},),
        mean_confidence=0.9,
    )

    result = assess_hybrid_ocr(
        selected_raw_text="+2335500...",
        selected_tokens=(),
        provider_code="GENERIC_MOMO",
        fraud_candidates=(candidate,),
        image_height=1280,
    )

    assert "GENUINE_TEMPLATE_ANOMALY" not in result.reason_codes
    assert result.profile_status == "NOT_APPLICABLE"


def test_v3_persisted_projection_is_validated_and_rebuilds_fixed_copy() -> None:
    persisted = finalize_hybrid_assessment(
        _consensus("NUMERIC_SENDER_TRANSACTION_CLAIM", "GENUINE_TEMPLATE_ANOMALY"),
        evidence_quality="HIGH",
        sender=SenderContext("phone_number", 0.95, True, False, "ocr_header"),
    ).as_public_dict()
    persisted["reasons"][0]["summary"] = "injected private value 0244000000"

    projection = stored_hybrid_assessment_projection(persisted)
    serialized = json.dumps(projection)

    assert projection["schema_version"] == HYBRID_SCHEMA_VERSION
    assert projection["class"] == "FRAUDULENT"
    assert "injected private value" not in serialized
    assert "0244000000" not in serialized

    persisted["class"] = "SUSPICIOUS"
    invalid = stored_hybrid_assessment_projection(persisted)
    assert invalid["status"] == "UNAVAILABLE"
    assert invalid["class"] is None


def test_shared_stored_projection_dispatches_v3_without_recomputing_ocr() -> None:
    persisted = finalize_hybrid_assessment(
        _consensus("NUMERIC_SENDER_TRANSACTION_CLAIM", "GENUINE_TEMPLATE_ANOMALY"),
        evidence_quality="HIGH",
    ).as_public_dict()

    projection = stored_text_assessment_projection(persisted)

    assert projection["ruleset_version"] == HYBRID_RULESET_VERSION
    assert projection["class"] == "FRAUDULENT"


def test_public_v3_projection_contains_no_private_candidate_fields() -> None:
    result = finalize_hybrid_assessment(
        _consensus("NUMERIC_SENDER_TRANSACTION_CLAIM", "GENUINE_TEMPLATE_ANOMALY"),
        evidence_quality="HIGH",
        sender=SenderContext("phone_number", 0.95, True, False, "ocr_header"),
    ).as_public_dict()
    serialized = json.dumps(result)

    assert "raw_text" not in serialized
    assert "matched_text" not in serialized
    assert "candidate_id" not in serialized
    assert "closest_signature_id" not in serialized
    assert result["score_is_probability"] is False
