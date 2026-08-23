from __future__ import annotations

from momo_fdvs.contracts.evidence import EvidenceMode, RiskBand
from momo_fdvs.services.risk_policy import AnalysisPolicyResult, PolicyReason
from momo_fdvs.services.risk_presentation import high_risk_summary, risk_tone


def test_counterfeit_pair_has_specific_high_risk_copy() -> None:
    assert (
        high_risk_summary({"NUMERIC_SENDER_TRANSACTION_CLAIM", "GENUINE_TEMPLATE_ANOMALY"})
        == "Likely counterfeit transaction notification"
    )


def test_active_scam_reason_has_active_scam_copy() -> None:
    assert high_risk_summary({"PIN_OR_OTP_REQUEST"}) == "Strong scam indicators detected"


def test_other_high_risk_reasons_use_generic_copy() -> None:
    assert high_risk_summary({"MODEL_HIGH_RISK"}) == "Multiple high-risk indicators detected"


def test_counterfeit_pair_takes_precedence_over_active_scam_copy() -> None:
    assert (
        high_risk_summary(
            {
                "NUMERIC_SENDER_TRANSACTION_CLAIM",
                "GENUINE_TEMPLATE_ANOMALY",
                "URGENCY_PRESSURE",
            }
        )
        == "Likely counterfeit transaction notification"
    )


def test_persisted_high_risk_policy_summary_uses_reason_codes() -> None:
    result = AnalysisPolicyResult(
        policy_version="analysis-risk-policy-demo-v4",
        policy_sha256="0" * 64,
        evidence_mode=EvidenceMode.SCREENSHOT_ONLY,
        status="PARTIAL",
        band=RiskBand.HIGH,
        legacy_risk_class="FRAUDULENT",
        score=None,
        reasons=(
            PolicyReason(
                "PIN_OR_OTP_REQUEST",
                "Secret code requested",
                "CRITICAL",
            ),
        ),
        missing_signals=(),
        limitations=(),
    )

    assert result.summary == "Strong scam indicators detected"


def test_risk_tone_uses_the_shared_four_band_mapping() -> None:
    assert risk_tone("low_risk") == "success"
    assert risk_tone("medium_risk") == "warning"
    assert risk_tone("high_risk") == "error"
    assert risk_tone("inconclusive") == "info"
