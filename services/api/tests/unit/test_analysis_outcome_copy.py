from __future__ import annotations

from momo_fdvs.services import notifications


def test_partial_high_notification_leads_with_the_conclusive_risk() -> None:
    copy_factory = getattr(notifications, "analysis_outcome_copy", None)

    assert callable(copy_factory)
    title, message = copy_factory(analysis_status="PARTIAL", risk_band="high_risk")
    assert title == "Analysis ready"
    assert "high fraud-risk result" in message.casefold()
    assert "optional evidence components were unavailable" in message.casefold()
    assert "inconclusive" not in message.casefold()


def test_partial_inconclusive_notification_names_insufficient_evidence() -> None:
    copy_factory = getattr(notifications, "analysis_outcome_copy", None)

    assert callable(copy_factory)
    _title, message = copy_factory(analysis_status="PARTIAL", risk_band="inconclusive")
    assert "insufficient" in message.casefold()
    assert "fraud-risk conclusion" in message.casefold()
