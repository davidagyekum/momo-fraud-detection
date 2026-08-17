from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from momo_fdvs.services.reports import render_analysis_report


def test_partial_high_report_separates_conclusion_from_component_availability() -> None:
    transaction = SimpleNamespace(
        provider_code="MTN_MOMO",
        display_reference_masked="CTRL...1234",
    )
    run = SimpleNamespace(
        status="PARTIAL",
        risk_class="FRAUDULENT",
        top_reasons=[],
        component_scores={
            "policy": {
                "status": "PARTIAL",
                "band": "high_risk",
                "legacy_risk_class": "FRAUDULENT",
                "score": None,
                "summary": "Configured high-risk evidence requires human review.",
                "reasons": [
                    {
                        "code": "PIN_OR_OTP_REQUEST",
                        "title": "Secret code requested",
                        "severity": "CRITICAL",
                    }
                ],
                "missing_signals": ["IMAGE_MODEL_NOT_ACTIVE"],
                "limitations": [],
                "policy_version": "controlled-policy-v2",
            },
            "image_model": {"status": "UNAVAILABLE"},
        },
        configuration_snapshot={"policy_version": "controlled-policy-v2"},
    )
    confirmation = SimpleNamespace(confirmed_fields={"amount": "125.00"})

    html = render_analysis_report(
        transaction,
        run,
        confirmation,
        None,
        generated_at=datetime(2026, 8, 17, tzinfo=UTC),
    ).decode("utf-8")

    assert "Conclusion</th><td>Conclusive" in html
    assert "Component availability</th><td>Degraded" in html
    assert "Some optional evidence components were unavailable" in html
    assert "persisted result is inconclusive" not in html.casefold()
