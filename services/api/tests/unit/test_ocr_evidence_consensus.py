from __future__ import annotations

from momo_fdvs.services.ocr_evidence_consensus import (
    CandidateEvidence,
    aggregate_candidate_evidence,
)


def _candidate(
    name: str,
    codes: tuple[str, ...],
    confidence: float = 0.9,
    *,
    evidence_group_id: str | None = None,
    margin: float | None = None,
    spelling: int = 0,
    formatting: int = 0,
) -> CandidateEvidence:
    return CandidateEvidence(
        candidate_id=name,
        evidence_group_id=evidence_group_id or name,
        region_kind="MESSAGE_BUBBLE",
        variant="GRAY",
        psm=6,
        ocr_confidence=confidence,
        reason_codes=codes,
        format_margin=margin,
        spelling_anomaly_count=spelling,
        formatting_anomaly_count=formatting,
    )


def test_spelling_and_format_need_two_candidate_votes() -> None:
    result = aggregate_candidate_evidence(
        [
            _candidate("a", ("FINANCIAL_TERM_SPELLING_ANOMALY", "MALFORMED_FINANCIAL_FORMAT")),
            _candidate("b", ("FINANCIAL_TERM_SPELLING_ANOMALY", "MALFORMED_FINANCIAL_FORMAT")),
        ]
    )

    assert result.accepted_reason_codes == (
        "FINANCIAL_TERM_SPELLING_ANOMALY",
        "MALFORMED_FINANCIAL_FORMAT",
    )


def test_single_typo_candidate_is_rejected() -> None:
    result = aggregate_candidate_evidence(
        [_candidate("a", ("FINANCIAL_TERM_SPELLING_ANOMALY",), 0.75, spelling=2)]
    )

    assert result.accepted_reason_codes == ()


def test_single_strong_detailed_spelling_and_format_candidates_are_accepted() -> None:
    result = aggregate_candidate_evidence(
        [
            _candidate(
                "a",
                ("FINANCIAL_TERM_SPELLING_ANOMALY", "MALFORMED_FINANCIAL_FORMAT"),
                0.82,
                spelling=3,
                formatting=3,
            )
        ]
    )

    assert result.accepted_reason_codes == (
        "FINANCIAL_TERM_SPELLING_ANOMALY",
        "MALFORMED_FINANCIAL_FORMAT",
    )


def test_variants_from_one_crop_count_as_one_reason_vote() -> None:
    result = aggregate_candidate_evidence(
        [
            _candidate(
                "body-gray-6",
                ("FINANCIAL_TERM_SPELLING_ANOMALY",),
                0.75,
                evidence_group_id="body-crop",
                spelling=2,
            ),
            _candidate(
                "body-clahe-11",
                ("FINANCIAL_TERM_SPELLING_ANOMALY",),
                0.78,
                evidence_group_id="body-crop",
                spelling=2,
            ),
        ]
    )

    assert result.vote_counts["FINANCIAL_TERM_SPELLING_ANOMALY"] == 1
    assert result.accepted_reason_codes == ()


def test_independent_crops_count_as_independent_reason_votes() -> None:
    result = aggregate_candidate_evidence(
        [
            _candidate(
                "body-gray-6",
                ("FINANCIAL_TERM_SPELLING_ANOMALY",),
                0.75,
                evidence_group_id="body-crop",
                spelling=2,
            ),
            _candidate(
                "bubble-gray-6",
                ("FINANCIAL_TERM_SPELLING_ANOMALY",),
                0.76,
                evidence_group_id="bubble-crop",
                spelling=2,
            ),
        ]
    )

    assert result.vote_counts["FINANCIAL_TERM_SPELLING_ANOMALY"] == 2
    assert result.accepted_reason_codes == ("FINANCIAL_TERM_SPELLING_ANOMALY",)


def test_strong_sender_and_large_template_margin_can_be_accepted_once() -> None:
    result = aggregate_candidate_evidence(
        [
            _candidate("header", ("NUMERIC_SENDER_TRANSACTION_CLAIM",), 0.91),
            _candidate("body", ("GENUINE_TEMPLATE_ANOMALY",), 0.88, margin=0.30),
        ]
    )

    assert result.accepted_reason_codes == (
        "GENUINE_TEMPLATE_ANOMALY",
        "NUMERIC_SENDER_TRANSACTION_CLAIM",
    )


def test_weak_single_sender_and_template_signals_are_rejected() -> None:
    result = aggregate_candidate_evidence(
        [
            _candidate("header", ("NUMERIC_SENDER_TRANSACTION_CLAIM",), 0.71),
            _candidate("body", ("GENUINE_TEMPLATE_ANOMALY",), 0.9, margin=0.11),
        ]
    )

    assert result.accepted_reason_codes == ()


def test_unknown_codes_and_candidate_details_never_reach_public_output() -> None:
    result = aggregate_candidate_evidence(
        [
            _candidate("private-coordinate-100-200", ("INJECTED_PRIVATE_REASON",)),
            _candidate("private-coordinate-300-400", ("INJECTED_PRIVATE_REASON",)),
        ]
    )
    public = result.as_public_dict()

    assert result.accepted_reason_codes == ()
    assert "INJECTED_PRIVATE_REASON" not in str(public)
    assert "private-coordinate" not in str(public)
    assert "strongest_confidence" not in public
    assert "evidence_group_id" not in str(public)


def test_empty_consensus_is_explicitly_limited() -> None:
    result = aggregate_candidate_evidence([])

    assert result.candidate_count == 0
    assert result.limitations == ("OCR_CANDIDATE_EVIDENCE_UNAVAILABLE",)
