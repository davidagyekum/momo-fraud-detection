"""Privacy-safe presentation derived only from allowlisted risk reason codes."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

ACTIVE_SCAM_REASON_CODES: Final = frozenset(
    {
        "PIN_OR_OTP_REQUEST",
        "WRONG_TRANSFER_REFUND_LURE",
        "ACCOUNT_BLOCK_THREAT_WITH_ACTION",
        "PAY_TO_UNLOCK_OR_RELEASE",
        "SUSPICIOUS_LINK_ACCOUNT_ACTION",
        "UNVERIFIED_CONTACT_REDIRECT",
        "PRIZE_OR_BONUS_LURE",
        "URGENCY_PRESSURE",
        "UNOFFICIAL_SENDER_CONTEXT",
    }
)
_COUNTERFEIT_PAIR: Final = frozenset(
    {"NUMERIC_SENDER_TRANSACTION_CLAIM", "GENUINE_TEMPLATE_ANOMALY"}
)


def high_risk_summary(reason_codes: Iterable[str]) -> str:
    """Return fixed high-risk copy without incorporating dynamic evidence values."""

    codes = frozenset(reason_codes)
    if codes >= _COUNTERFEIT_PAIR:
        return "Likely counterfeit transaction notification"
    if codes & ACTIVE_SCAM_REASON_CODES:
        return "Strong scam indicators detected"
    return "Multiple high-risk indicators detected"


__all__ = ["ACTIVE_SCAM_REASON_CODES", "high_risk_summary"]
