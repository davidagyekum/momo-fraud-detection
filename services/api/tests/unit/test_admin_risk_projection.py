from __future__ import annotations

from types import SimpleNamespace

from momo_fdvs.api.v1.operations import _policy_summary


def test_admin_high_risk_summary_is_rebuilt_from_safe_reason_codes() -> None:
    run = SimpleNamespace(
        component_scores={
            "policy": {
                "band": "high_risk",
                "summary": "injected private summary 0244000000",
                "reasons": [
                    {
                        "code": "PIN_OR_OTP_REQUEST",
                        "title": "Secret code requested",
                        "severity": "CRITICAL",
                    }
                ],
            }
        }
    )

    assert _policy_summary(run) == "Strong scam indicators detected"


def test_admin_non_high_summary_uses_fixed_stored_policy_copy() -> None:
    run = SimpleNamespace(
        component_scores={
            "policy": {
                "band": "medium_risk",
                "summary": "Configured risk indicators require caution and human review.",
                "reasons": [],
            }
        }
    )

    assert _policy_summary(run) == (
        "Configured risk indicators require caution and human review."
    )
