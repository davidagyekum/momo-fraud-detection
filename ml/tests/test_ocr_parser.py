from __future__ import annotations

from datetime import UTC, datetime

import pytest

from momo_fdvs_ml.ocr_parser import (
    FIELD_CONFIDENCE_THRESHOLD,
    detect_provider,
    parse_amount,
    parse_momo_text,
    parse_recipient,
    parse_reference,
    parse_status,
    parse_timestamp,
    parse_wallet,
    redacted_log_summary,
)

NOW = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)


def _complete_text() -> str:
    return (
        "MTN MobileMoney\n"
        "Payment made to Demo Merchant\n"
        "Recipient phone: 024 000 0012\n"
        "Amount: GHS 1,250.50\n"
        "Transaction ID: AB12CD34EF\n"
        "Date/Time: 14/08/2026 10:30\n"
        "Status: Successful"
    )


def test_parser_returns_versioned_complete_result_and_preserves_raw_values() -> None:
    result = parse_momo_text(_complete_text(), engine_confidence=0.9, now=NOW)

    assert result.provider.normalized == "MTN_MOMO"
    assert result.template_family == "mtn_momo_transaction"
    assert result.fields["amount"].raw == "1,250.50"
    assert result.fields["amount"].normalized == "1250.50"
    assert result.fields["reference"].normalized == "AB12CD34EF"
    assert result.fields["recipient"].normalized == "DEMO MERCHANT"
    assert result.fields["recipient_wallet"].normalized == "+233240000012"
    assert result.fields["timestamp"].normalized == "2026-08-14T10:30:00Z"
    assert result.fields["status"].normalized == "successful"
    assert result.inconclusive is False
    payload = result.as_dict()
    assert payload["parser_version"] == result.parser_version
    assert payload["fields"]["amount"]["raw"] == "1,250.50"  # type: ignore[index]


@pytest.mark.parametrize(
    ("text", "normalized", "warning"),
    [
        ("Amount GHS 10", "10.00", None),
        ("Paid GH₵ 1,001.2", "1001.20", None),
        ("Total GH¢ 0.05", "0.05", None),
        ("GHC 20.00 paid", "20.00", None),
        ("Balance GHS 10.00", "10.00", None),
        ("Amount GHS 10.00 and total GHS 20.00", None, "AMOUNT_AMBIGUOUS"),
        ("Amount GHS 10.123", None, "AMOUNT_NOT_FOUND"),
        ("No value here", None, "AMOUNT_NOT_FOUND"),
    ],
)
def test_amount_normalization_and_ambiguity(
    text: str, normalized: str | None, warning: str | None
) -> None:
    field = parse_amount(text)
    assert field.normalized == normalized
    if warning:
        assert warning in field.warnings


def test_reference_preserves_ocr_ambiguity_and_never_silently_corrects() -> None:
    field = parse_reference("Reference: AB0OI2345")
    assert field.raw == "AB0OI2345"
    assert field.normalized == "AB0OI2345"
    assert field.confidence < FIELD_CONFIDENCE_THRESHOLD
    assert field.warnings == ("REFERENCE_OI_AMBIGUITY_PRESERVED",)
    assert parse_reference("nothing").normalized is None
    assert parse_reference("Reference: $bad").warnings == ("REFERENCE_NOT_FOUND",)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Recipient: Demo Person", "DEMO PERSON"),
        ("Payment made to Demo Shop on 14/08/2026", "DEMO SHOP"),
        ("Cash In received from Demo Sender at 10:30", "DEMO SENDER"),
        ("No counterparty", None),
    ],
)
def test_recipient_normalization_keeps_meaningful_content(text: str, expected: str | None) -> None:
    assert parse_recipient(text).normalized == expected


@pytest.mark.parametrize(
    ("text", "expected", "warning"),
    [
        ("Wallet: 0240000012", "+233240000012", None),
        ("Call +233 24 000 0012", "+233240000012", None),
        ("One 0240000012 two 0550000013", None, "WALLET_AMBIGUOUS"),
        ("Wallet: 123", None, "WALLET_NOT_FOUND"),
        ("No wallet", None, "WALLET_NOT_FOUND"),
    ],
)
def test_wallet_normalization_is_ghana_specific(
    text: str, expected: str | None, warning: str | None
) -> None:
    field = parse_wallet(text)
    assert field.normalized == expected
    if warning:
        assert warning in field.warnings


@pytest.mark.parametrize(
    ("text", "expected", "warning"),
    [
        ("Date 2026-08-14 10:30:05", "2026-08-14T10:30:05Z", None),
        ("On 14-08-26 10:30", "2026-08-14T10:30:00Z", None),
        (
            "Time: 08/09/2026 10:30",
            "2026-09-08T10:30:00Z",
            "DATE_ORDER_AMBIGUOUS_DAY_FIRST_USED",
        ),
        ("Date: 31/02/2026 10:30", None, "TIMESTAMP_FORMAT_INVALID"),
        ("No timestamp", None, "TIMESTAMP_NOT_FOUND"),
    ],
)
def test_timestamp_uses_explicit_accra_utc_and_flags_ambiguous_order(
    text: str, expected: str | None, warning: str | None
) -> None:
    field = parse_timestamp(text)
    assert field.normalized == expected
    if warning:
        assert warning in field.warnings


@pytest.mark.parametrize(
    ("text", "expected", "warning"),
    [
        ("Status completed", "successful", None),
        ("The transfer failed", "failed", None),
        ("Reversal completed", "unknown", "STATUS_CONFLICT"),
        ("Awaiting action", "unknown", "STATUS_UNKNOWN"),
    ],
)
def test_status_never_defaults_unknown_to_success(
    text: str, expected: str, warning: str | None
) -> None:
    field = parse_status(text)
    assert field.normalized == expected
    if warning:
        assert warning in field.warnings


def test_unknown_template_is_not_itself_high_risk_and_missing_fields_are_inconclusive() -> None:
    result = parse_momo_text("Unrecognized notice with no transaction fields", now=NOW)
    assert result.provider.normalized == "UNKNOWN"
    assert result.semantic_reason_codes == ("TEMPLATE_UNKNOWN", "STATUS_UNKNOWN")
    assert result.inconclusive is True
    assert "HIGH_RISK" not in result.semantic_reason_codes


def test_provider_conflicts_and_semantics_are_deterministic_with_explicit_clock() -> None:
    text = _complete_text().replace("MTN MobileMoney", "MTN MobileMoney Telecel")
    text = text.replace("14/08/2026 10:30", "15/08/2026 12:30")
    text += "\nBalance GHS 5.00"
    result = parse_momo_text(text, now=NOW)
    assert result.provider.normalized == "UNKNOWN"
    assert set(result.semantic_reason_codes) == {
        "TEMPLATE_UNKNOWN",
        "TIMESTAMP_IN_FUTURE",
        "MULTIPLE_DISTINCT_AMOUNTS",
        "PROVIDER_BODY_CONFLICT",
    }


def test_naive_semantic_clock_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        parse_momo_text(_complete_text(), now=datetime(2026, 8, 14, 12, 0))


def test_low_engine_confidence_makes_critical_fields_inconclusive() -> None:
    result = parse_momo_text(_complete_text(), engine_confidence=0.0, now=NOW)
    assert result.fields["recipient"].confidence < FIELD_CONFIDENCE_THRESHOLD
    assert result.inconclusive is True


def test_redacted_log_summary_contains_no_raw_text_or_normalized_values() -> None:
    result = parse_momo_text(_complete_text(), now=NOW)
    summary = redacted_log_summary(result)
    serialized = str(summary)
    assert "Demo Merchant" not in serialized
    assert "1250.50" not in serialized
    assert "AB12CD34EF" not in serialized
    assert summary["field_availability"]["amount"] is True  # type: ignore[index]


def test_provider_detection_prefers_stronger_anchor_set() -> None:
    assert detect_provider("MTN MobileMoney receipt").normalized == "MTN_MOMO"
    assert detect_provider("Telecel Cash alert").normalized == "TELECEL_CASH"
    assert detect_provider("AirtelTigo Money").normalized == "AIRTELTIGO_MONEY"
    assert detect_provider("generic wallet").normalized == "UNKNOWN"
