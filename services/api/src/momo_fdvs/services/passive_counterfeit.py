"""Extract privacy-safe passive-counterfeit evidence from one OCR candidate."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from momo_fdvs.services.financial_message_evidence import analyze_language_and_format
from momo_fdvs.services.mtn_format_profile import LoadedMtnFormatProfile
from momo_fdvs.services.ocr_evidence_consensus import CandidateEvidence
from momo_fdvs.services.sender_context import SenderContext


@dataclass(frozen=True)
class PassiveCandidateResult:
    evidence: CandidateEvidence
    sender: SenderContext
    family: str
    format_available: bool
    format_anomalous: bool | None


def assess_passive_candidate(
    *,
    candidate_id: str,
    evidence_group_id: str,
    region_kind: str,
    variant: str,
    psm: int,
    raw_text: str,
    tokens: Iterable[dict[str, Any]],
    ocr_confidence: float,
    sender: SenderContext,
    format_profile: LoadedMtnFormatProfile | None,
) -> PassiveCandidateResult:
    """Extract candidate evidence without performing a final fraud classification."""

    token_rows = list(tokens)
    language = analyze_language_and_format(raw_text, token_rows)
    reasons: set[str] = set()
    if (
        language.transaction_claim
        and sender.sender_kind in {"phone_number", "mixed"}
        and sender.sender_confidence >= 0.72
        and sender.header_phone_present
    ):
        reasons.add("NUMERIC_SENDER_TRANSACTION_CLAIM")

    family = "OTHER"
    format_available = False
    format_anomalous: bool | None = None
    format_margin: float | None = None
    if format_profile is not None and language.transaction_claim:
        match = format_profile.match_text(raw_text)
        family = match.family
        format_available = match.status == "AVAILABLE"
        format_anomalous = match.anomalous
        if match.anomalous:
            reasons.add("GENUINE_TEMPLATE_ANOMALY")
        if match.similarity is not None and match.threshold is not None:
            format_margin = max(0.0, match.threshold - match.similarity)
    if language.spelling_anomaly_count >= 2:
        reasons.add("FINANCIAL_TERM_SPELLING_ANOMALY")
    if language.formatting_anomaly_count >= 2:
        reasons.add("MALFORMED_FINANCIAL_FORMAT")

    evidence = CandidateEvidence(
        candidate_id=candidate_id,
        evidence_group_id=evidence_group_id,
        region_kind=region_kind,
        variant=variant,
        psm=psm,
        ocr_confidence=max(0.0, min(1.0, float(ocr_confidence))),
        reason_codes=tuple(sorted(reasons)),
        format_margin=format_margin,
        spelling_anomaly_count=language.spelling_anomaly_count,
        formatting_anomaly_count=language.formatting_anomaly_count,
    )
    return PassiveCandidateResult(
        evidence=evidence,
        sender=sender,
        family=family,
        format_available=format_available,
        format_anomalous=format_anomalous,
    )


__all__ = ["PassiveCandidateResult", "assess_passive_candidate"]
