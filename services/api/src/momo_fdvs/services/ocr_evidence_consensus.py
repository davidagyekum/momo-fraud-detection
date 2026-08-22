"""Consensus over bounded OCR regions, variants, and page-segmentation modes."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

_PASSIVE_CODES: Final = frozenset(
    {
        "NUMERIC_SENDER_TRANSACTION_CLAIM",
        "GENUINE_TEMPLATE_ANOMALY",
        "FINANCIAL_TERM_SPELLING_ANOMALY",
        "MALFORMED_FINANCIAL_FORMAT",
    }
)
_ACTIVE_CODES: Final = frozenset(
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
_ALLOWED_CODES: Final = _PASSIVE_CODES | _ACTIVE_CODES


@dataclass(frozen=True)
class CandidateEvidence:
    candidate_id: str
    region_kind: str
    variant: str
    psm: int
    ocr_confidence: float
    reason_codes: tuple[str, ...]
    format_margin: float | None = None
    spelling_anomaly_count: int = 0
    formatting_anomaly_count: int = 0


@dataclass(frozen=True)
class ConsensusEvidence:
    accepted_reason_codes: tuple[str, ...]
    vote_counts: dict[str, int]
    strongest_confidence: dict[str, float]
    candidate_count: int
    limitations: tuple[str, ...]

    def as_public_dict(self) -> dict[str, object]:
        """Return allowlisted aggregates without candidates, OCR text, or geometry."""

        return {
            "accepted_reason_codes": list(self.accepted_reason_codes),
            "vote_counts": dict(sorted(self.vote_counts.items())),
            "candidate_count": self.candidate_count,
            "limitations": list(self.limitations),
        }


def aggregate_candidate_evidence(
    candidates: Iterable[CandidateEvidence],
) -> ConsensusEvidence:
    rows = list(candidates)
    votes: Counter[str] = Counter()
    strongest: dict[str, float] = {}
    best_margin: dict[str, float] = {}
    spelling_counts: dict[str, int] = {}
    formatting_counts: dict[str, int] = {}
    for candidate in rows:
        confidence = max(0.0, min(1.0, float(candidate.ocr_confidence)))
        for code in set(candidate.reason_codes) & _ALLOWED_CODES:
            votes[code] += 1
            strongest[code] = max(strongest.get(code, 0.0), confidence)
            if candidate.format_margin is not None:
                best_margin[code] = max(best_margin.get(code, 0.0), candidate.format_margin)
            spelling_counts[code] = max(
                spelling_counts.get(code, 0), candidate.spelling_anomaly_count
            )
            formatting_counts[code] = max(
                formatting_counts.get(code, 0), candidate.formatting_anomaly_count
            )

    accepted: list[str] = []
    for code in sorted(votes):
        count = votes[code]
        confidence = strongest.get(code, 0.0)
        if code == "NUMERIC_SENDER_TRANSACTION_CLAIM":
            if count >= 1 and confidence >= 0.72:
                accepted.append(code)
        elif code == "GENUINE_TEMPLATE_ANOMALY":
            if count >= 2 or (
                count == 1 and confidence >= 0.72 and best_margin.get(code, 0.0) >= 0.12
            ):
                accepted.append(code)
        elif code == "FINANCIAL_TERM_SPELLING_ANOMALY":
            if count >= 2 or (
                count == 1 and confidence >= 0.82 and spelling_counts.get(code, 0) >= 3
            ):
                accepted.append(code)
        elif code == "MALFORMED_FINANCIAL_FORMAT":
            if count >= 2 or (
                count == 1 and confidence >= 0.82 and formatting_counts.get(code, 0) >= 3
            ):
                accepted.append(code)
        elif code in _ACTIVE_CODES and (count >= 2 or confidence >= 0.82):
            accepted.append(code)

    limitations: list[str] = []
    if not rows:
        limitations.append("OCR_CANDIDATE_EVIDENCE_UNAVAILABLE")
    elif len(rows) == 1:
        limitations.append("SINGLE_OCR_CANDIDATE_ONLY")
    return ConsensusEvidence(
        accepted_reason_codes=tuple(accepted),
        vote_counts=dict(votes),
        strongest_confidence=strongest,
        candidate_count=len(rows),
        limitations=tuple(limitations),
    )


__all__ = ["CandidateEvidence", "ConsensusEvidence", "aggregate_candidate_evidence"]
