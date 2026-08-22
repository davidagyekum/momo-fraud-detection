"""Versioned hybrid fraud assessment for active scams and passive counterfeits."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any, Final, Literal, cast

from momo_fdvs.services.mtn_format_profile import (
    LoadedMtnFormatProfile,
    MtnFormatProfileError,
    load_bundled_mtn_profile,
)
from momo_fdvs.services.ocr_evidence_consensus import (
    CandidateEvidence,
    ConsensusEvidence,
    aggregate_candidate_evidence,
)
from momo_fdvs.services.passive_counterfeit import assess_passive_candidate
from momo_fdvs.services.sender_context import SenderContext, infer_sender_context
from momo_fdvs.services.text_fraud import TextFraudContext, assess_ocr_text

Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
RiskClass = Literal["SUSPICIOUS", "FRAUDULENT"]
EvidenceQuality = Literal["HIGH", "MEDIUM", "LOW", "UNAVAILABLE"]

HYBRID_SCHEMA_VERSION: Final = "momo-hybrid-text-risk-assessment-v1"
HYBRID_RULESET_VERSION: Final = "ghana-momo-hybrid-text-risk-v3"

_REASON_DETAILS: Final[dict[str, tuple[str, str, Severity]]] = {
    "PIN_OR_OTP_REQUEST": (
        "Secret code requested",
        "The message asks the user to disclose a PIN, OTP or security code.",
        "CRITICAL",
    ),
    "WRONG_TRANSFER_REFUND_LURE": (
        "Wrong-transfer or refund lure",
        "The message claims money was sent by mistake and asks for an unverified return.",
        "CRITICAL",
    ),
    "PAY_TO_UNLOCK_OR_RELEASE": (
        "Payment demanded to unlock funds",
        "The message demands a fee or transfer before funds or an account will be released.",
        "CRITICAL",
    ),
    "ACCOUNT_BLOCK_THREAT_WITH_ACTION": (
        "Account threat with demanded action",
        "The message threatens an account restriction and directs an unverified action.",
        "HIGH",
    ),
    "SUSPICIOUS_LINK_ACCOUNT_ACTION": (
        "Suspicious account-action link",
        "The message includes an unverified link for an account or transaction action.",
        "HIGH",
    ),
    "UNVERIFIED_CONTACT_REDIRECT": (
        "Redirected to an unverified contact",
        "The message redirects an issue to an ordinary phone or messaging contact.",
        "HIGH",
    ),
    "PRIZE_OR_BONUS_LURE": (
        "Prize or bonus lure",
        "The message offers a prize or bonus and asks the user to take another action.",
        "HIGH",
    ),
    "URGENCY_PRESSURE": (
        "Urgency or pressure language",
        "The message pressures the user to act immediately or before a short deadline.",
        "MEDIUM",
    ),
    "UNOFFICIAL_SENDER_CONTEXT": (
        "Unofficial sender context",
        "A provider claim appears under a normal phone-number sender.",
        "LOW",
    ),
    "NUMERIC_SENDER_TRANSACTION_CLAIM": (
        "Transaction claim under a numeric sender",
        "The screenshot presents a financial notification under a numeric sender header.",
        "HIGH",
    ),
    "GENUINE_TEMPLATE_ANOMALY": (
        "Message structure differs from reviewed MTN formats",
        "The structure differs substantially from the privacy-safe genuine-format profile.",
        "HIGH",
    ),
    "FINANCIAL_TERM_SPELLING_ANOMALY": (
        "Multiple financial terms appear misspelled",
        "Several independently recognized financial terms differ from reviewed vocabulary.",
        "MEDIUM",
    ),
    "MALFORMED_FINANCIAL_FORMAT": (
        "Financial fields use malformed formatting",
        "Multiple balance, fee, currency or identifier formatting anomalies were detected.",
        "MEDIUM",
    ),
}
_SEVERITY_ORDER: Final[dict[Severity, int]] = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}
_ALLOWED_LIMITATIONS: Final = frozenset(
    {
        "OCR_CANDIDATE_EVIDENCE_UNAVAILABLE",
        "SINGLE_OCR_CANDIDATE_ONLY",
        "OCR_CONFIDENCE_LOW",
        "OCR_TEXT_EMPTY",
        "OCR_TEXT_SHORT",
        "MTN_FORMAT_PROFILE_UNAVAILABLE",
        "MTN_FORMAT_PROFILE_INTEGRITY_FAILURE",
        "MTN_FORMAT_PROFILE_SCHEMA_INVALID",
        "MTN_FORMAT_PROFILE_CONFIGURATION_INVALID",
        "HYBRID_ASSESSMENT_NOT_PERSISTED",
    }
)
_QUALITY_ORDER: Final[dict[EvidenceQuality, int]] = {
    "UNAVAILABLE": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
}


@dataclass(frozen=True)
class HybridReason:
    code: str
    title: str
    summary: str
    severity: Severity

    def as_public_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class HybridAssessment:
    schema_version: str
    ruleset_version: str
    status: str
    risk_class: RiskClass | None
    risk_score: int | None
    reason_code: str
    reasons: tuple[HybridReason, ...]
    evidence_quality: EvidenceQuality
    limitations: tuple[str, ...]
    consensus: ConsensusEvidence
    sender: SenderContext
    profile_status: str
    profile_version: str | None
    profile_sha256: str | None
    score_is_probability: bool = False

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return tuple(reason.code for reason in self.reasons)

    def as_public_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "ruleset_version": self.ruleset_version,
            "status": self.status,
            "class": self.risk_class,
            "score": self.risk_score,
            "score_is_probability": self.score_is_probability,
            "reason_code": self.reason_code,
            "reason_codes": list(self.reason_codes),
            "reasons": [reason.as_public_dict() for reason in self.reasons],
            "evidence_quality": self.evidence_quality,
            "limitations": list(self.limitations),
            "summary": _summary(self.risk_class),
            "disclaimer": (
                "This is a screenshot-evidence risk assessment, not live confirmation from a "
                "mobile-network operator or a legal determination."
            ),
            "evidence": {
                "sender": self.sender.as_public_dict(),
                "consensus": self.consensus.as_public_dict(),
                "format_profile": {
                    "status": self.profile_status,
                    "version": self.profile_version,
                    "sha256": self.profile_sha256,
                },
            },
        }


def _summary(risk_class: RiskClass | None) -> str:
    if risk_class == "FRAUDULENT":
        return "The screenshot contains strong fraud indicators and should be treated as high risk."
    if risk_class == "SUSPICIOUS":
        return "The screenshot contains suspicious evidence requiring independent verification."
    return (
        "The available evidence did not support a reliable fraud classification. "
        "This is not a genuine or safe verdict."
    )


def _reason(code: str) -> HybridReason:
    title, summary, severity = _REASON_DETAILS[code]
    return HybridReason(code, title, summary, severity)


def _base_reason_codes(base_assessment: Mapping[str, object] | None) -> set[str]:
    if not base_assessment or not isinstance(base_assessment.get("reason_codes"), list):
        return set()
    return {
        code
        for code in cast(list[object], base_assessment["reason_codes"])
        if isinstance(code, str) and code in _REASON_DETAILS
    }


def _classification(
    reasons: tuple[HybridReason, ...],
) -> tuple[RiskClass | None, int | None, str]:
    critical_count = sum(reason.severity == "CRITICAL" for reason in reasons)
    high_count = sum(reason.severity == "HIGH" for reason in reasons)
    medium_count = sum(reason.severity == "MEDIUM" for reason in reasons)
    if critical_count >= 1:
        return (
            "FRAUDULENT",
            min(100, 95 + 2 * (critical_count - 1) + min(high_count, 2)),
            "OBVIOUS_SCAM_EVIDENCE_DETECTED",
        )
    if high_count >= 2:
        return (
            "FRAUDULENT",
            min(98, 90 + 2 * (high_count - 2) + min(medium_count, 2)),
            "CORROBORATED_COUNTERFEIT_OR_SCAM_EVIDENCE",
        )
    if high_count == 1:
        return (
            "SUSPICIOUS",
            min(82, 68 + 4 * min(medium_count, 2)),
            "HIGH_RISK_EVIDENCE_REQUIRES_REVIEW",
        )
    if medium_count >= 2:
        return "SUSPICIOUS", 56, "MULTIPLE_AUTHENTICITY_ANOMALIES"
    return None, None, "INCONCLUSIVE_SCREENSHOT_EVIDENCE"


def finalize_hybrid_assessment(
    consensus: ConsensusEvidence,
    *,
    base_assessment: Mapping[str, object] | None = None,
    evidence_quality: EvidenceQuality,
    sender: SenderContext | None = None,
    profile_status: str = "UNAVAILABLE",
    profile_version: str | None = None,
    profile_sha256: str | None = None,
    additional_limitations: Iterable[str] = (),
) -> HybridAssessment:
    codes = set(consensus.accepted_reason_codes) | _base_reason_codes(base_assessment)
    reasons = tuple(
        sorted(
            (_reason(code) for code in codes if code in _REASON_DETAILS),
            key=lambda item: (-_SEVERITY_ORDER[item.severity], item.code),
        )
    )
    risk_class, score, reason_code = _classification(reasons)
    limitations = tuple(
        sorted((set(consensus.limitations) | set(additional_limitations)) & _ALLOWED_LIMITATIONS)
    )
    return HybridAssessment(
        HYBRID_SCHEMA_VERSION,
        HYBRID_RULESET_VERSION,
        "SUCCESS" if reasons or consensus.candidate_count else "UNAVAILABLE",
        risk_class,
        score,
        reason_code,
        reasons,
        evidence_quality,
        limitations,
        consensus,
        sender or SenderContext("unknown", 0.0, False, False, "none"),
        profile_status,
        profile_version,
        profile_sha256,
    )


def _profile() -> tuple[LoadedMtnFormatProfile | None, str, str | None, str | None, list[str]]:
    try:
        profile = load_bundled_mtn_profile()
    except MtnFormatProfileError as exc:
        limitation = f"MTN_FORMAT_{exc.code}"
        return None, "UNAVAILABLE", None, None, [limitation]
    return (
        profile,
        "AVAILABLE",
        profile.schema_version,
        profile.profile_sha256,
        [],
    )


def _quality_max(values: Iterable[str]) -> EvidenceQuality:
    typed = [cast(EvidenceQuality, value) for value in values if value in _QUALITY_ORDER]
    return max(typed, key=lambda value: _QUALITY_ORDER[value], default="UNAVAILABLE")


def assess_hybrid_ocr(
    *,
    selected_raw_text: str,
    selected_tokens: Iterable[dict[str, Any]],
    provider_code: str,
    fraud_candidates: Iterable[Any],
    image_height: int,
) -> HybridAssessment:
    """Assess the selected OCR text plus bounded fraud-oriented OCR candidates."""

    selected_token_rows = list(selected_tokens)
    candidates = list(fraud_candidates)
    all_tokens = list(selected_token_rows)
    for candidate in candidates:
        all_tokens.extend(list(getattr(candidate, "tokens", ())))
    sender = infer_sender_context(
        all_tokens,
        image_height=image_height,
        raw_text=selected_raw_text,
    )
    profile, profile_status, profile_version, profile_sha256, limitations = _profile()
    context = TextFraudContext(
        sender_kind=sender.sender_kind,
        claimed_provider=provider_code,
    )
    base = assess_ocr_text(
        selected_raw_text,
        ocr_confidence=None,
        context=context,
    )
    qualities = [base.evidence_quality]
    evidence_rows: list[CandidateEvidence] = []
    for candidate in candidates:
        raw_text = str(getattr(candidate, "raw_text", ""))
        tokens = tuple(getattr(candidate, "tokens", ()))
        confidence = float(getattr(candidate, "mean_confidence", 0.0))
        passive = assess_passive_candidate(
            candidate_id=str(getattr(candidate, "candidate_id", "candidate")),
            region_kind=str(getattr(candidate, "region_kind", "UNKNOWN")),
            variant=str(getattr(candidate, "variant", "UNKNOWN")),
            psm=int(getattr(candidate, "psm", 0)),
            raw_text=raw_text,
            tokens=tokens,
            ocr_confidence=confidence,
            sender=sender,
            format_profile=profile,
        )
        active = assess_ocr_text(raw_text, ocr_confidence=confidence, context=context)
        qualities.append(active.evidence_quality)
        evidence_rows.append(
            CandidateEvidence(
                candidate_id=passive.evidence.candidate_id,
                region_kind=passive.evidence.region_kind,
                variant=passive.evidence.variant,
                psm=passive.evidence.psm,
                ocr_confidence=passive.evidence.ocr_confidence,
                reason_codes=tuple(
                    sorted(set(passive.evidence.reason_codes) | set(active.reason_codes))
                ),
                format_margin=passive.evidence.format_margin,
                spelling_anomaly_count=passive.evidence.spelling_anomaly_count,
                formatting_anomaly_count=passive.evidence.formatting_anomaly_count,
            )
        )
    consensus = aggregate_candidate_evidence(evidence_rows)
    limitations.extend(
        limitation
        for limitation in base.limitations
        if limitation in {"OCR_CONFIDENCE_LOW", "OCR_TEXT_EMPTY", "OCR_TEXT_SHORT"}
    )
    return finalize_hybrid_assessment(
        consensus,
        base_assessment=base.as_public_dict(),
        evidence_quality=_quality_max(qualities),
        sender=sender,
        profile_status=profile_status,
        profile_version=profile_version,
        profile_sha256=profile_sha256,
        additional_limitations=limitations,
    )


def _unavailable_stored() -> HybridAssessment:
    return finalize_hybrid_assessment(
        ConsensusEvidence((), {}, {}, 0, ()),
        evidence_quality="UNAVAILABLE",
        additional_limitations=("HYBRID_ASSESSMENT_NOT_PERSISTED",),
    )


def stored_hybrid_assessment_projection(value: object) -> dict[str, object]:
    """Validate v3 evidence and rebuild all human-readable copy from fixed codes."""

    unavailable = _unavailable_stored()
    if not isinstance(value, dict):
        return unavailable.as_public_dict()
    reason_codes = value.get("reason_codes")
    evidence = value.get("evidence")
    limitations = value.get("limitations")
    if (
        value.get("schema_version") != HYBRID_SCHEMA_VERSION
        or value.get("ruleset_version") != HYBRID_RULESET_VERSION
        or value.get("score_is_probability") is not False
        or value.get("status") not in {"SUCCESS", "UNAVAILABLE"}
        or value.get("evidence_quality") not in _QUALITY_ORDER
        or not isinstance(reason_codes, list)
        or len(set(map(str, reason_codes))) != len(reason_codes)
        or any(not isinstance(code, str) or code not in _REASON_DETAILS for code in reason_codes)
        or not isinstance(limitations, list)
        or any(item not in _ALLOWED_LIMITATIONS for item in limitations)
        or not isinstance(evidence, dict)
    ):
        return unavailable.as_public_dict()
    sender_value = evidence.get("sender")
    consensus_value = evidence.get("consensus")
    profile_value = evidence.get("format_profile")
    if (
        not isinstance(sender_value, dict)
        or set(sender_value)
        != {
            "sender_kind",
            "sender_confidence",
            "header_phone_present",
            "header_provider_label_present",
            "source",
        }
        or sender_value["sender_kind"]
        not in {"phone_number", "alphanumeric_provider", "mixed", "unknown"}
        or isinstance(sender_value["sender_confidence"], bool)
        or not isinstance(sender_value["sender_confidence"], (int, float))
        or not 0 <= float(sender_value["sender_confidence"]) <= 1
        or not isinstance(sender_value["header_phone_present"], bool)
        or not isinstance(sender_value["header_provider_label_present"], bool)
        or sender_value["source"] not in {"ocr_header", "none"}
        or not isinstance(consensus_value, dict)
        or set(consensus_value)
        != {"accepted_reason_codes", "vote_counts", "candidate_count", "limitations"}
        or not isinstance(profile_value, dict)
        or set(profile_value) != {"status", "version", "sha256"}
    ):
        return unavailable.as_public_dict()
    accepted = consensus_value["accepted_reason_codes"]
    votes = consensus_value["vote_counts"]
    candidate_count = consensus_value["candidate_count"]
    consensus_limitations = consensus_value["limitations"]
    if (
        not isinstance(accepted, list)
        or any(not isinstance(code, str) or code not in _REASON_DETAILS for code in accepted)
        or not isinstance(votes, dict)
        or any(
            code not in _REASON_DETAILS
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 1
            for code, count in votes.items()
        )
        or isinstance(candidate_count, bool)
        or not isinstance(candidate_count, int)
        or not 0 <= candidate_count <= 32
        or not isinstance(consensus_limitations, list)
        or any(item not in _ALLOWED_LIMITATIONS for item in consensus_limitations)
        or profile_value["status"] not in {"AVAILABLE", "UNAVAILABLE"}
        or (profile_value["version"] is not None and not isinstance(profile_value["version"], str))
        or (profile_value["sha256"] is not None and not isinstance(profile_value["sha256"], str))
    ):
        return unavailable.as_public_dict()
    consensus = ConsensusEvidence(
        tuple(cast(list[str], accepted)),
        cast(dict[str, int], votes),
        {},
        candidate_count,
        tuple(cast(list[str], consensus_limitations)),
    )
    sender = SenderContext(
        cast(Any, sender_value["sender_kind"]),
        float(sender_value["sender_confidence"]),
        sender_value["header_phone_present"],
        sender_value["header_provider_label_present"],
        sender_value["source"],
    )
    base_codes = set(cast(list[str], reason_codes)) - set(consensus.accepted_reason_codes)
    rebuilt = finalize_hybrid_assessment(
        consensus,
        base_assessment={"reason_codes": sorted(base_codes)},
        evidence_quality=cast(EvidenceQuality, value["evidence_quality"]),
        sender=sender,
        profile_status=profile_value["status"],
        profile_version=profile_value["version"],
        profile_sha256=profile_value["sha256"],
        additional_limitations=cast(list[str], limitations),
    )
    if (
        value.get("status") != rebuilt.status
        or value.get("class") != rebuilt.risk_class
        or value.get("score") != rebuilt.risk_score
        or value.get("reason_code") != rebuilt.reason_code
        or reason_codes != list(rebuilt.reason_codes)
    ):
        return unavailable.as_public_dict()
    return rebuilt.as_public_dict()


__all__ = [
    "HYBRID_RULESET_VERSION",
    "HYBRID_SCHEMA_VERSION",
    "HybridAssessment",
    "HybridReason",
    "assess_hybrid_ocr",
    "finalize_hybrid_assessment",
    "stored_hybrid_assessment_projection",
]
