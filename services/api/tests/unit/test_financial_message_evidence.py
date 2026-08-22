from __future__ import annotations

from typing import Any

from momo_fdvs.services.financial_message_evidence import analyze_language_and_format


def _tokens(*values: tuple[str, float]) -> list[dict[str, Any]]:
    return [{"text": text, "confidence": confidence} for text, confidence in values]


def test_controlled_counterfeit_has_multiple_spelling_and_format_anomalies() -> None:
    result = analyze_language_and_format(
        "Cash In for Gh 700.00 carent bulance.700.04 "
        "avelabil bulance.700.04 ID: 90000000000001 FEE: 00.000",
        _tokens(("carent", 92), ("bulance", 94), ("avelabil", 90)),
    )

    assert result.transaction_claim is True
    assert result.spelling_anomaly_count >= 2
    assert result.spelling_codes == ("MULTIPLE_FINANCIAL_TERM_MISSPELLINGS",)
    assert result.formatting_anomaly_count >= 3
    assert {
        "NONSTANDARD_CURRENCY_MARKER",
        "BALANCE_VALUE_JOINED_TO_LABEL",
        "FEE_HAS_MORE_THAN_TWO_DECIMALS",
        "BARE_ID_LABEL_IN_TRANSACTION_MESSAGE",
    } <= set(result.formatting_codes)


def test_one_possible_ocr_typo_does_not_create_spelling_reason() -> None:
    result = analyze_language_and_format(
        "Payment made for GHS 10.00. Current balanse GHS 20.00.",
        _tokens(("balanse", 93)),
    )

    assert result.spelling_anomaly_count == 1
    assert result.spelling_codes == ()


def test_low_confidence_tokens_are_not_spelling_evidence() -> None:
    result = analyze_language_and_format(
        "Cash In for GHS 10.00 carent bulance",
        _tokens(("carent", 30), ("bulance", 35)),
    )

    assert result.spelling_anomaly_count == 0


def test_genuine_cash_in_has_no_language_or_format_anomaly() -> None:
    result = analyze_language_and_format(
        "Cash In received for GHS 10.00 from SAMPLE SHOP. Current Balance GHS 20.00 "
        "Available Balance GHS 20.00. Transaction ID: 123456789. Fee charged: GHS 0.",
        _tokens(("Current", 95), ("Balance", 95), ("Available", 95)),
    )

    assert result.formatting_anomaly_count == 0
    assert result.spelling_anomaly_count == 0


def test_advisory_and_marketing_messages_are_not_transaction_claims() -> None:
    advisory = analyze_language_and_format(
        "Never share your PIN or OTP with anyone claiming to verify a transaction.",
        _tokens(("transaction", 96)),
    )
    marketing = analyze_language_and_format(
        "Enjoy a GHS 10 bonus when you download the MoMo app.",
        _tokens(("bonus", 95)),
    )

    assert advisory.transaction_claim is False
    assert marketing.transaction_claim is False
    assert advisory.as_public_dict()["formatting_codes"] == []
    assert marketing.as_public_dict()["spelling_codes"] == []


def test_public_evidence_contains_no_tokens_or_financial_values() -> None:
    result = analyze_language_and_format(
        "Cash In for Gh 700.00 carent bulance.700.04 avelabil bulance.700.04",
        _tokens(("carent", 92), ("bulance", 94), ("avelabil", 90)),
    )
    public = str(result.as_public_dict())

    assert "carent" not in public
    assert "bulance" not in public
    assert "avelabil" not in public
    assert "700.04" not in public
