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
    "text, expected_code, expected_class",
    [
        (
            (
                "Dear customer, your MoMo wallet has been blocked. "
                "Call 0244000000 immediately to reactivate it."
            ),
            "ACCOUNT_BLOCK_THREAT_WITH_ACTION",
            "FRAUDULENT",
        ),
        (
            "I sent money to you by mistake. Kindly refund GHS 500 to 0550000000 now.",
            "WRONG_TRANSFER_REFUND_LURE",
            "FRAUDULENT",
        ),
        (
            "MTN customer care: send your MoMo PIN and OTP to 0244000000 for verification.",
            "PIN_OR_OTP_REQUEST",
            "FRAUDULENT",
        ),
        (
            "Pay a processing fee of GHS 50 to unlock and release your mobile money funds.",
            "PAY_TO_UNLOCK_OR_RELEASE",
            "FRAUDULENT",
        ),
        (
            (
                "Final notice: verify your MoMo account at "
                "http://momo-check.example/login immediately."
            ),
            "SUSPICIOUS_LINK_ACCOUNT_ACTION",
            "SUSPICIOUS",
        ),
        (
            "Congratulations, you have won a MoMo bonus. Call 0550000000 to claim your prize.",
            "PRIZE_OR_BONUS_LURE",
            "FRAUDULENT",
        ),
    ],
)
def test_obvious_scam_text_uses_independent_family_thresholds(
    text: str,
    expected_code: str,
    expected_class: str,
) -> None:
    result = assess_ocr_text(text, ocr_confidence=0.84)

    assert result.status == "SUCCESS"
    assert result.risk_class == expected_class
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


def test_contrastive_clause_cannot_extend_an_advisory_over_a_secret_request() -> None:
    result = assess_ocr_text(
        "Never share your PIN, but send your OTP now to keep the wallet active.",
        ocr_confidence=0.9,
    )

    assert result.risk_class == "FRAUDULENT"
    assert "PIN_OR_OTP_REQUEST" in result.reason_codes


def test_all_unicode_format_controls_are_removed_before_matching() -> None:
    result = assess_ocr_text(
        "S\u2066e\u2069n\u00add your O\u200fTP now to keep the wallet active.",
        ocr_confidence=0.9,
    )

    assert result.risk_class == "FRAUDULENT"
    assert "PIN_OR_OTP_REQUEST" in result.reason_codes


def test_compound_cues_outside_an_adjacent_clause_window_do_not_combine() -> None:
    result = assess_ocr_text(
        "Pay your normal bill. The fee statement is ready. The notice says release funds.",
        ocr_confidence=0.9,
    )

    assert "PAY_TO_UNLOCK_OR_RELEASE" not in result.reason_codes
    assert result.risk_class is None


def test_scheme_less_short_link_needs_account_or_credential_action() -> None:
    corroborated = assess_ocr_text(
        "Log in to your MoMo account at bit.ly/momo-check to confirm it.",
        ocr_confidence=0.9,
    )
    uncorroborated = assess_ocr_text(
        "Read the community promotion news at bit.ly/momo-check.",
        ocr_confidence=0.9,
    )

    assert corroborated.risk_class == "SUSPICIOUS"
    assert "SUSPICIOUS_LINK_ACCOUNT_ACTION" in corroborated.reason_codes
    assert "SUSPICIOUS_LINK_ACCOUNT_ACTION" not in uncorroborated.reason_codes


def test_international_contact_redirect_is_cautious_without_a_second_high_family() -> None:
    result = assess_ocr_text(
        "Contact MoMo support on +44 20 7946 0958 about your account.",
        ocr_confidence=0.9,
    )

    assert result.risk_class == "SUSPICIOUS"
    assert result.reason_codes == ("UNVERIFIED_CONTACT_REDIRECT",)


def test_single_high_family_plus_urgency_remains_suspicious() -> None:
    result = assess_ocr_text(
        "Urgent: your wallet is blocked. Submit details now to reactivate it.",
        ocr_confidence=0.9,
    )

    assert result.risk_class == "SUSPICIOUS"
    assert "ACCOUNT_BLOCK_THREAT_WITH_ACTION" in result.reason_codes
    assert "URGENCY_PRESSURE" in result.reason_codes


def test_two_independent_high_families_are_fraudulent() -> None:
    result = assess_ocr_text(
        "Your MoMo wallet is blocked. Log in at bit.ly/momo-check to restore your account.",
        ocr_confidence=0.9,
    )

    assert result.risk_class == "FRAUDULENT"
    assert "ACCOUNT_BLOCK_THREAT_WITH_ACTION" in result.reason_codes
    assert "SUSPICIOUS_LINK_ACCOUNT_ACTION" in result.reason_codes


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


def test_historical_v1_projection_keeps_its_original_high_plus_urgency_result() -> None:
    projection = stored_text_assessment_projection(
        {
            "schema_version": "momo-text-fraud-assessment-v1",
            "ruleset_version": "ghana-momo-obvious-scam-rules-v1",
            "status": "SUCCESS",
            "class": "FRAUDULENT",
            "score": 82,
            "score_is_probability": False,
            "reason_code": "CORROBORATED_SCAM_TEXT",
            "reason_codes": ["ACCOUNT_BLOCK_THREAT_WITH_ACTION", "URGENCY_PRESSURE"],
            "reasons": [],
            "evidence_quality": "HIGH",
            "limitations": [],
        }
    )

    assert projection["ruleset_version"] == "ghana-momo-obvious-scam-rules-v1"
    assert projection["class"] == "FRAUDULENT"
    assert projection["score"] == 82


def test_new_assessments_use_the_v2_ruleset() -> None:
    result = assess_ocr_text("Send your OTP now.", ocr_confidence=0.9)

    assert result.ruleset_version == "ghana-momo-obvious-scam-rules-v2"


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
