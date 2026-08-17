from __future__ import annotations

import json

import pytest

from momo_fdvs.services.text_fraud import (
    TEXT_FRAUD_RULESET_VERSION,
    TextFraudContext,
    assess_ocr_text,
    stored_text_assessment_projection,
)


@pytest.mark.parametrize(
    "text, expected_code",
    [
        (
            (
                "Dear customer, your MoMo wallet has been blocked. "
                "Call 0244000000 immediately to reactivate it."
            ),
            "ACCOUNT_BLOCK_THREAT_WITH_ACTION",
        ),
        (
            "I sent money to you by mistake. Kindly refund GHS 500 to 0550000000 now.",
            "WRONG_TRANSFER_REFUND_LURE",
        ),
        (
            "MTN customer care: send your MoMo PIN and OTP to 0244000000 for verification.",
            "PIN_OR_OTP_REQUEST",
        ),
        (
            "Pay a processing fee of GHS 50 to unlock and release your mobile money funds.",
            "PAY_TO_UNLOCK_OR_RELEASE",
        ),
        (
            (
                "Final notice: verify your MoMo account at "
                "http://momo-check.example/login immediately."
            ),
            "SUSPICIOUS_LINK_ACCOUNT_ACTION",
        ),
        (
            "Congratulations, you have won a MoMo bonus. Call 0550000000 to claim your prize.",
            "PRIZE_OR_BONUS_LURE",
        ),
    ],
)
def test_obvious_scam_text_is_fraudulent(text: str, expected_code: str) -> None:
    result = assess_ocr_text(text, ocr_confidence=0.84)

    assert result.status == "SUCCESS"
    assert result.risk_class == "FRAUDULENT"
    assert result.risk_score is not None and result.risk_score >= 80
    assert expected_code in result.reason_codes
    assert result.ruleset_version == TEXT_FRAUD_RULESET_VERSION


@pytest.mark.parametrize(
    "text",
    [
        "Never share your MoMo PIN or OTP with anyone. MTN will never ask for it.",
        "Payment of GHS 25.00 to DEMO SHOP was successful. Transaction ID ABC12345.",
        "Reversal completed successfully. Reference REV123456.",
        "Refund completed successfully. Reference REF123456.",
        "You have received GHS 10.00 from TEST USER. Available balance is GHS 40.00.",
    ],
)
def test_normal_or_advisory_text_is_not_falsely_called_fraud(text: str) -> None:
    result = assess_ocr_text(text, ocr_confidence=0.9)

    assert result.risk_class != "FRAUDULENT"
    assert "PIN_OR_OTP_REQUEST" not in result.reason_codes


@pytest.mark.parametrize(
    "text",
    [
        "Enter the OTP shown on your phone to complete sign in.",
        "Your account was temporarily locked. Visit an official service centre for help.",
        "Contact customer care through the official app if you do not recognise this payment.",
    ],
)
def test_legitimate_security_or_support_instructions_are_not_called_fraud(
    text: str,
) -> None:
    result = assess_ocr_text(text, ocr_confidence=0.9)

    assert result.risk_class != "FRAUDULENT"
    assert "PIN_OR_OTP_REQUEST" not in result.reason_codes
    assert "ACCOUNT_BLOCK_THREAT_WITH_ACTION" not in result.reason_codes


def test_advisory_sentence_cannot_hide_a_separate_secret_request() -> None:
    result = assess_ocr_text(
        "Never share your PIN with strangers.\nSend your OTP to 0244000000 now.",
        ocr_confidence=0.9,
    )

    assert result.risk_class == "FRAUDULENT"
    assert "PIN_OR_OTP_REQUEST" in result.reason_codes


def test_legitimate_reversal_status_with_support_contact_is_not_a_wrong_transfer_lure() -> None:
    result = assess_ocr_text(
        "Reversal pending. Contact customer care on 0244000000 for assistance.",
        ocr_confidence=0.9,
    )

    assert "WRONG_TRANSFER_REFUND_LURE" not in result.reason_codes
    assert result.risk_class != "FRAUDULENT"


def test_numeric_sender_is_only_corroborating_evidence() -> None:
    context = TextFraudContext(sender_kind="phone_number", claimed_provider="MTN_MOMO")
    result = assess_ocr_text(
        "MTN MobileMoney payment notification.",
        ocr_confidence=0.9,
        context=context,
    )

    assert result.risk_class is None
    assert result.reason_codes == ("UNOFFICIAL_SENDER_CONTEXT",)
    replay = stored_text_assessment_projection(result.as_public_dict())
    assert replay["class"] is None
    assert replay["reason_codes"] == ["UNOFFICIAL_SENDER_CONTEXT"]


def test_low_ocr_confidence_does_not_hide_a_critical_secret_request() -> None:
    result = assess_ocr_text(
        "Reply with your OTP and PIN now to keep your wallet active.",
        ocr_confidence=0.1,
    )

    assert result.risk_class == "FRAUDULENT"
    assert result.evidence_quality == "LOW"
    assert "OCR_CONFIDENCE_LOW" in result.limitations


def test_empty_or_unreadable_ocr_is_unavailable() -> None:
    result = assess_ocr_text("  ", ocr_confidence=0.0)

    assert result.status == "UNAVAILABLE"
    assert result.risk_class is None
    assert result.risk_score is None
    assert result.reason_code == "OCR_TEXT_UNAVAILABLE"


def test_assessment_projection_never_persists_raw_text_or_matches() -> None:
    sample_message = "Send OTP 731991 to +233244000000"
    result = assess_ocr_text(sample_message, ocr_confidence=0.8)
    payload = result.as_public_dict()
    serialized = json.dumps(payload)

    assert "731991" not in serialized
    assert "+233244000000" not in serialized
    assert "raw_text" not in serialized
    assert "matched_text" not in serialized
    assert payload["ruleset_version"] == TEXT_FRAUD_RULESET_VERSION


def test_stored_projection_reconstructs_fixed_reasons_instead_of_trusting_text() -> None:
    persisted = assess_ocr_text(
        "Send your PIN and OTP to 0244000000 now.",
        ocr_confidence=0.9,
    ).as_public_dict()
    persisted["reasons"][0]["summary"] = "private injected value 0244000000"

    projection = stored_text_assessment_projection(persisted)
    serialized = json.dumps(projection)

    assert projection["class"] == "FRAUDULENT"
    assert "private injected value" not in serialized
    assert "0244000000" not in serialized

    persisted["class"] = "SUSPICIOUS"
    invalid = stored_text_assessment_projection(persisted)
    assert invalid["status"] == "UNAVAILABLE"
    assert invalid["reason_code"] == "OCR_TEXT_ASSESSMENT_NOT_PERSISTED"


def test_legacy_stored_projection_is_unavailable_without_recomputation() -> None:
    projection = stored_text_assessment_projection({"raw_text": "Send your PIN now"})

    assert projection["status"] == "UNAVAILABLE"
    assert projection["class"] is None
    assert projection["score"] is None
    assert projection["reason_code"] == "OCR_TEXT_ASSESSMENT_NOT_PERSISTED"


def test_obfuscated_ocr_variants_are_detected() -> None:
    result = assess_ocr_text(
        "P1ease sh@re your 0TP security c0de and M0M0 P1N to verify your wa11et.",
        ocr_confidence=0.55,
    )

    assert result.risk_class == "FRAUDULENT"
    assert "PIN_OR_OTP_REQUEST" in result.reason_codes


def test_rule_order_and_output_are_deterministic() -> None:
    text = "Urgent: send your PIN and OTP to 0244000000 to unlock your wallet."
    first = assess_ocr_text(text, ocr_confidence=0.8).as_public_dict()
    second = assess_ocr_text(text, ocr_confidence=0.8).as_public_dict()

    assert first == second
    assert first["reason_codes"] == sorted(first["reason_codes"])


def test_ocr_token_confidence_accepts_percent_and_fraction_scales() -> None:
    from momo_fdvs.services.text_fraud import confidence_from_ocr_tokens

    assert (
        confidence_from_ocr_tokens([{"confidence": 80}, {"confidence": 0.6}, {"confidence": -1}])
        == 0.7
    )
    assert confidence_from_ocr_tokens([], fallback=0.55) == 0.55
