"""Versioned evidence-aware policy for persisted receipt analyses."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from momo_fdvs.contracts.evidence import EvidenceMode, RiskBand, legacy_risk_from_band

AnalysisStatus = Literal["COMPLETED", "PARTIAL"]
ModelKind = Literal["IMAGE", "STRUCTURED"]
TextSignalStatus = Literal["SUCCESS", "UNAVAILABLE"]
ReasonSeverity = Literal["INFORMATIONAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

ANALYSIS_RESULT_CONTRACT_VERSION = "analysis-result-v1"
POLICY_SCHEMA_VERSION = "analysis-risk-policy-schema-v1"
_REASON_CODE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_POLICY_KEYS = {
    "schema_version",
    "policy_version",
    "critical_verification_fields",
    "structured_class_bands",
    "text_class_bands",
    "text_fraud_ruleset_version",
    "text_policy_score_is_probability",
    "image_high_threshold",
    "categorical_score_is_null",
    "deterministic_image_supporting_only",
    "stored_reference_match_is_not_low_risk",
}
_STRUCTURED_CLASSES = {"GENUINE", "SUSPICIOUS", "FRAUDULENT"}
_TEXT_CLASSES = {"SUSPICIOUS", "FRAUDULENT"}
_IMAGE_CLASSES = {"unaltered", "tampered"}
_VERIFICATION_STATUSES = {"VERIFIED", "MISMATCH", "UNVERIFIED", "NOT_ATTEMPTED"}
_SEVERITIES = {"INFORMATIONAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"}


class PolicyFailure(ValueError):
    """A fail-closed policy contract error safe for public translation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _validate_reason_codes(reason_codes: tuple[str, ...]) -> None:
    if not reason_codes or len(set(reason_codes)) != len(reason_codes):
        raise PolicyFailure(
            "RISK_POLICY_INPUT_INVALID", "Model reason codes must be present and unique."
        )
    if any(_REASON_CODE.fullmatch(code) is None for code in reason_codes):
        raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Model reason codes are invalid.")


@dataclass(frozen=True)
class PolicyReason:
    """One safe and deterministic explanation emitted by the policy."""

    code: str
    title: str
    severity: ReasonSeverity

    def __post_init__(self) -> None:
        if _REASON_CODE.fullmatch(self.code) is None:
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Policy reason code is invalid.")
        if not self.title.strip() or self.severity not in _SEVERITIES:
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Policy reason is invalid.")

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "title": self.title, "severity": self.severity}


@dataclass(frozen=True)
class ModelPolicySignal:
    """Nullable model evidence with exact artifact and schema identity."""

    kind: ModelKind
    available: bool
    score: float | None
    predicted_class: str | None
    reason_codes: tuple[str, ...]
    model_version: str | None = None
    artifact_sha256: str | None = None
    schema_hash: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"IMAGE", "STRUCTURED"}:
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Model kind is invalid.")
        _validate_reason_codes(self.reason_codes)
        if not self.available:
            if any(
                value is not None
                for value in (
                    self.score,
                    self.predicted_class,
                    self.model_version,
                    self.artifact_sha256,
                    self.schema_hash,
                )
            ):
                raise PolicyFailure(
                    "RISK_POLICY_INPUT_INVALID",
                    "Unavailable model signals must keep values and identities null.",
                )
            return
        if (
            isinstance(self.score, bool)
            or not isinstance(self.score, (int, float))
            or not math.isfinite(float(self.score))
            or not 0 <= float(self.score) <= 1
        ):
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Model score is invalid.")
        if not self.model_version or _SHA256.fullmatch(self.artifact_sha256 or "") is None:
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Model identity is invalid.")
        if _SHA256.fullmatch(self.schema_hash or "") is None:
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Model schema identity is invalid.")
        if self.kind == "IMAGE" and self.predicted_class not in _IMAGE_CLASSES:
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "The image model class is invalid.")
        if self.kind == "STRUCTURED" and self.predicted_class not in _STRUCTURED_CLASSES:
            raise PolicyFailure(
                "RISK_POLICY_INPUT_INVALID", "The structured model class is invalid."
            )

    @classmethod
    def unavailable(cls, kind: ModelKind, reason_code: str) -> ModelPolicySignal:
        return cls(
            kind=kind,
            available=False,
            score=None,
            predicted_class=None,
            reason_codes=(reason_code,),
        )


@dataclass(frozen=True)
class TextPolicySignal:
    """Versioned deterministic OCR-text evidence; its score is never a probability."""

    status: TextSignalStatus
    predicted_class: str | None
    policy_score: int | None
    score_is_probability: bool
    reason_codes: tuple[str, ...]
    reasons: tuple[PolicyReason, ...]
    ruleset_version: str | None
    schema_version: str | None
    evidence_quality: str | None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {"SUCCESS", "UNAVAILABLE"}:
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Text signal status is invalid.")
        _validate_reason_codes(self.reason_codes)
        if self.score_is_probability:
            raise PolicyFailure(
                "RISK_POLICY_INPUT_INVALID", "The text policy score cannot be a probability."
            )
        if any(_REASON_CODE.fullmatch(code) is None for code in self.limitations):
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Text limitations are invalid.")
        if not set(reason.code for reason in self.reasons).issubset(self.reason_codes):
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Text reasons are inconsistent.")
        if self.status == "UNAVAILABLE":
            if self.predicted_class is not None or self.policy_score is not None or self.reasons:
                raise PolicyFailure(
                    "RISK_POLICY_INPUT_INVALID",
                    "Unavailable text evidence must not contain a class, score, or reasons.",
                )
            return
        if not self.ruleset_version or not self.schema_version:
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Text evidence identity is invalid.")
        if self.evidence_quality not in {"HIGH", "MEDIUM", "LOW"}:
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Text evidence quality is invalid.")
        if self.predicted_class is None:
            if self.policy_score is not None:
                raise PolicyFailure(
                    "RISK_POLICY_INPUT_INVALID", "Inconclusive text evidence must keep score null."
                )
            return
        if self.predicted_class not in _TEXT_CLASSES:
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Text risk class is invalid.")
        if (
            isinstance(self.policy_score, bool)
            or not isinstance(self.policy_score, int)
            or not 0 <= self.policy_score <= 100
        ):
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Text policy score is invalid.")

    @classmethod
    def unavailable(cls, reason_code: str) -> TextPolicySignal:
        return cls(
            status="UNAVAILABLE",
            predicted_class=None,
            policy_score=None,
            score_is_probability=False,
            reason_codes=(reason_code,),
            reasons=(),
            ruleset_version=None,
            schema_version=None,
            evidence_quality=None,
        )


@dataclass(frozen=True)
class AnalysisPolicyInput:
    """All evidence the policy may use for one immutable analysis."""

    mode: EvidenceMode
    verification_status: str
    critical_verification_mismatches: tuple[str, ...]
    confirmed_critical_fields_complete: bool
    corrected_low_confidence_fields: tuple[str, ...]
    deterministic_image_reasons: tuple[PolicyReason, ...]
    image_model: ModelPolicySignal
    structured_model: ModelPolicySignal
    semantic_reasons: tuple[PolicyReason, ...]
    text_signal: TextPolicySignal = field(
        default_factory=lambda: TextPolicySignal.unavailable("OCR_TEXT_RISK_UNAVAILABLE")
    )

    def __post_init__(self) -> None:
        if not isinstance(self.mode, EvidenceMode):
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Evidence mode is invalid.")
        if self.verification_status not in _VERIFICATION_STATUSES:
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Verification status is invalid.")
        if self.image_model.kind != "IMAGE" or self.structured_model.kind != "STRUCTURED":
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Model evidence is misaligned.")
        if not isinstance(self.text_signal, TextPolicySignal):
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Text evidence is invalid.")
        if any(not field.strip() for field in self.corrected_low_confidence_fields):
            raise PolicyFailure("RISK_POLICY_INPUT_INVALID", "Correction field is invalid.")


@dataclass(frozen=True)
class LoadedRiskPolicy:
    """Strict policy configuration plus its canonical byte identity."""

    policy_version: str
    policy_sha256: str
    critical_verification_fields: tuple[str, ...]
    structured_class_bands: dict[str, RiskBand]
    text_class_bands: dict[str, RiskBand]
    text_fraud_ruleset_version: str
    text_policy_score_is_probability: bool
    image_high_threshold: float
    categorical_score_is_null: bool
    deterministic_image_supporting_only: bool
    stored_reference_match_is_not_low_risk: bool


@dataclass(frozen=True)
class AnalysisPolicyResult:
    """Persistable policy result with no fabricated probability."""

    policy_version: str
    policy_sha256: str
    evidence_mode: EvidenceMode
    status: AnalysisStatus
    band: RiskBand
    legacy_risk_class: str | None
    score: float | None
    reasons: tuple[PolicyReason, ...]
    missing_signals: tuple[str, ...]
    limitations: tuple[str, ...]

    @property
    def conclusion_status(self) -> str:
        """Describe whether the risk band itself is decisive."""

        return "INCONCLUSIVE" if self.band is RiskBand.INCONCLUSIVE else "CONCLUSIVE"

    @property
    def component_status(self) -> str:
        """Describe evidence-component completeness independently from risk."""

        return "DEGRADED" if self.status == "PARTIAL" else "COMPLETE"

    @property
    def summary(self) -> str:
        return {
            RiskBand.LOW: "Supported model evidence indicates a low configured risk band.",
            RiskBand.MEDIUM: "Configured risk indicators require caution and human review.",
            RiskBand.HIGH: "Configured high-risk evidence requires human review.",
            RiskBand.INCONCLUSIVE: (
                "The available evidence is insufficient for a fraud-risk conclusion."
            ),
        }[self.band]

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_version": ANALYSIS_RESULT_CONTRACT_VERSION,
            "policy_version": self.policy_version,
            "policy_sha256": self.policy_sha256,
            "evidence_mode": self.evidence_mode.value,
            "status": self.status,
            "band": self.band.value,
            "conclusion_status": self.conclusion_status,
            "component_status": self.component_status,
            "legacy_risk_class": self.legacy_risk_class,
            "score": self.score,
            "reasons": [reason.as_dict() for reason in self.reasons],
            "missing_signals": list(self.missing_signals),
            "limitations": list(self.limitations),
            "summary": self.summary,
        }


@dataclass(frozen=True)
class FinalizationSemantics:
    """Safe terminal copy and codes derived from separate risk/component states."""

    error_code: str | None
    safe_message: str | None
    conclusion_status: str
    component_status: str


def derive_finalization_semantics(
    *,
    analysis_status: str,
    risk_band: RiskBand | str,
    missing_signals: tuple[str, ...] = (),
) -> FinalizationSemantics:
    """Never call a decisive risk band inconclusive because components are missing."""

    try:
        band = risk_band if isinstance(risk_band, RiskBand) else RiskBand(risk_band)
    except ValueError:
        band = RiskBand.INCONCLUSIVE
    if analysis_status == "FAILED":
        return FinalizationSemantics(
            error_code="ANALYSIS_FAILED",
            safe_message="The analysis could not be completed.",
            conclusion_status="FAILED",
            component_status="FAILED",
        )
    component_status = "DEGRADED" if analysis_status == "PARTIAL" else "COMPLETE"
    if band is RiskBand.INCONCLUSIVE:
        return FinalizationSemantics(
            error_code="ANALYSIS_EVIDENCE_INCONCLUSIVE",
            safe_message=("The available evidence was insufficient for a fraud-risk conclusion."),
            conclusion_status="INCONCLUSIVE",
            component_status=component_status,
        )
    if analysis_status == "PARTIAL":
        suffix = " Some optional evidence components were unavailable." if missing_signals else ""
        return FinalizationSemantics(
            error_code="ANALYSIS_COMPONENTS_PARTIAL",
            safe_message=(
                f"A conclusive {band.value.replace('_', ' ')} result was produced from the "
                f"available evidence.{suffix}"
            ),
            conclusion_status="CONCLUSIVE",
            component_status="DEGRADED",
        )
    return FinalizationSemantics(
        error_code=None,
        safe_message=None,
        conclusion_status="CONCLUSIVE",
        component_status="COMPLETE",
    )


def _schema_failure() -> PolicyFailure:
    return PolicyFailure("RISK_POLICY_SCHEMA_INVALID", "The analysis risk policy is invalid.")


def load_risk_policy(path: Path, *, expected_sha256: str | None = None) -> LoadedRiskPolicy:
    """Load one strict local policy without exposing its path or content on failure."""

    try:
        raw = path.read_bytes()
    except OSError:
        raise PolicyFailure(
            "RISK_POLICY_UNAVAILABLE", "The analysis risk policy is unavailable."
        ) from None
    policy_sha256 = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None:
        if _SHA256.fullmatch(expected_sha256) is None:
            raise PolicyFailure(
                "RISK_POLICY_HASH_INVALID", "The expected risk policy hash is invalid."
            )
        if policy_sha256 != expected_sha256:
            raise PolicyFailure(
                "RISK_POLICY_HASH_MISMATCH",
                "The analysis risk policy failed integrity verification.",
            )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise _schema_failure() from None
    if not isinstance(payload, dict) or set(payload) != _POLICY_KEYS:
        raise _schema_failure()
    try:
        schema_version = payload["schema_version"]
        policy_version = payload["policy_version"]
        critical_fields = payload["critical_verification_fields"]
        band_values = payload["structured_class_bands"]
        text_band_values = payload["text_class_bands"]
        text_ruleset_version = payload["text_fraud_ruleset_version"]
        text_score_probability = payload["text_policy_score_is_probability"]
        threshold = payload["image_high_threshold"]
        categorical_null = payload["categorical_score_is_null"]
        supporting_only = payload["deterministic_image_supporting_only"]
        match_not_low = payload["stored_reference_match_is_not_low_risk"]
        if schema_version != POLICY_SCHEMA_VERSION:
            raise _schema_failure()
        if not isinstance(policy_version, str) or not policy_version.strip():
            raise _schema_failure()
        if (
            not isinstance(critical_fields, list)
            or not critical_fields
            or len(set(critical_fields)) != len(critical_fields)
            or any(not isinstance(value, str) or not value for value in critical_fields)
        ):
            raise _schema_failure()
        if not isinstance(band_values, dict) or set(band_values) != _STRUCTURED_CLASSES:
            raise _schema_failure()
        structured_bands = {name: RiskBand(value) for name, value in band_values.items()}
        if not isinstance(text_band_values, dict) or set(text_band_values) != _TEXT_CLASSES:
            raise _schema_failure()
        text_bands = {name: RiskBand(value) for name, value in text_band_values.items()}
        if text_bands != {
            "SUSPICIOUS": RiskBand.MEDIUM,
            "FRAUDULENT": RiskBand.HIGH,
        }:
            raise _schema_failure()
        if not isinstance(text_ruleset_version, str) or not text_ruleset_version.strip():
            raise _schema_failure()
        if text_score_probability is not False:
            raise _schema_failure()
        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, (int, float))
            or not math.isfinite(float(threshold))
            or not 0 < float(threshold) < 1
        ):
            raise _schema_failure()
        if (categorical_null, supporting_only, match_not_low) != (True, True, True):
            raise _schema_failure()
    except (KeyError, TypeError, ValueError, PolicyFailure):
        raise _schema_failure() from None
    return LoadedRiskPolicy(
        policy_version=policy_version,
        policy_sha256=policy_sha256,
        critical_verification_fields=tuple(critical_fields),
        structured_class_bands=structured_bands,
        text_class_bands=text_bands,
        text_fraud_ruleset_version=text_ruleset_version,
        text_policy_score_is_probability=text_score_probability,
        image_high_threshold=float(threshold),
        categorical_score_is_null=categorical_null,
        deterministic_image_supporting_only=supporting_only,
        stored_reference_match_is_not_low_risk=match_not_low,
    )


def _deduplicate(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _deduplicate_reasons(values: tuple[PolicyReason, ...]) -> tuple[PolicyReason, ...]:
    return tuple({value.code: value for value in reversed(values)}.values())[::-1]


def _limitations(value: AnalysisPolicyInput) -> tuple[str, ...]:
    limitations: list[str] = []
    if value.verification_status == "VERIFIED":
        limitations.append("STORED_REFERENCE_MATCH_NOT_AUTHENTICITY")
    if value.verification_status == "NOT_ATTEMPTED":
        limitations.append("REFERENCE_VERIFICATION_NOT_APPLICABLE")
    if value.deterministic_image_reasons:
        limitations.append("DETERMINISTIC_IMAGE_SUPPORTING_ONLY")
    if value.corrected_low_confidence_fields:
        limitations.append("CORRECTED_LOW_CONFIDENCE_FIELDS")
    limitations.extend(value.text_signal.limitations)
    return _deduplicate(tuple(limitations))


def _unavailable_model_signals(value: AnalysisPolicyInput) -> tuple[str, ...]:
    missing: tuple[str, ...] = ()
    if not value.image_model.available:
        missing += value.image_model.reason_codes
    if not value.structured_model.available:
        missing += value.structured_model.reason_codes
    return _deduplicate(missing)


def _result(
    policy: LoadedRiskPolicy,
    value: AnalysisPolicyInput,
    band: RiskBand,
    reasons: tuple[PolicyReason, ...],
) -> AnalysisPolicyResult:
    combined = _deduplicate_reasons(
        reasons
        + value.text_signal.reasons
        + value.semantic_reasons
        + value.deterministic_image_reasons
    )
    return AnalysisPolicyResult(
        policy_version=policy.policy_version,
        policy_sha256=policy.policy_sha256,
        evidence_mode=value.mode,
        status=(
            "COMPLETED"
            if value.image_model.available and value.structured_model.available
            else "PARTIAL"
        ),
        band=band,
        legacy_risk_class=legacy_risk_from_band(band),
        score=None,
        reasons=combined,
        missing_signals=_unavailable_model_signals(value),
        limitations=_limitations(value),
    )


def _inconclusive(
    policy: LoadedRiskPolicy,
    value: AnalysisPolicyInput,
    primary_missing_signal: str,
) -> AnalysisPolicyResult:
    missing = [primary_missing_signal]
    if not value.confirmed_critical_fields_complete:
        missing.append("CRITICAL_OCR_FIELDS_INCOMPLETE")
    if value.verification_status == "UNVERIFIED":
        missing.append("REFERENCE_RECORD_UNAVAILABLE")
    if value.text_signal.status == "UNAVAILABLE":
        missing.extend(value.text_signal.reason_codes)
    elif value.text_signal.predicted_class is None:
        missing.append("CONCLUSIVE_TEXT_EVIDENCE_UNAVAILABLE")
    missing.extend(_unavailable_model_signals(value))
    reasons = _deduplicate_reasons(
        (
            PolicyReason(
                code="INSUFFICIENT_EVIDENCE",
                title="Available evidence cannot support a fraud-risk conclusion",
                severity="INFORMATIONAL",
            ),
            *value.text_signal.reasons,
            *value.semantic_reasons,
            *value.deterministic_image_reasons,
        )
    )
    return AnalysisPolicyResult(
        policy_version=policy.policy_version,
        policy_sha256=policy.policy_sha256,
        evidence_mode=value.mode,
        status="PARTIAL",
        band=RiskBand.INCONCLUSIVE,
        legacy_risk_class=None,
        score=None,
        reasons=reasons,
        missing_signals=_deduplicate(tuple(missing)),
        limitations=_limitations(value),
    )


def _structured_reason(predicted_class: str) -> PolicyReason:
    return {
        "GENUINE": PolicyReason(
            "STRUCTURED_MODEL_LOW_RISK",
            "The accepted structured model emitted its low-risk class",
            "LOW",
        ),
        "SUSPICIOUS": PolicyReason(
            "STRUCTURED_MODEL_MEDIUM_RISK",
            "The accepted structured model emitted its review class",
            "MEDIUM",
        ),
        "FRAUDULENT": PolicyReason(
            "STRUCTURED_MODEL_HIGH_RISK",
            "The accepted structured model emitted its high-risk class",
            "HIGH",
        ),
    }[predicted_class]


def evaluate_risk_policy(
    policy: LoadedRiskPolicy, value: AnalysisPolicyInput
) -> AnalysisPolicyResult:
    """Evaluate fixed-priority evidence without averaging unlike signals."""

    unknown_mismatches = set(value.critical_verification_mismatches).difference(
        policy.critical_verification_fields
    )
    if unknown_mismatches:
        raise PolicyFailure(
            "RISK_POLICY_INPUT_INVALID", "Critical verification mismatch is invalid."
        )
    if (
        value.text_signal.status == "SUCCESS"
        and value.text_signal.ruleset_version != policy.text_fraud_ruleset_version
    ):
        raise PolicyFailure(
            "RISK_POLICY_INPUT_INVALID", "The text evidence ruleset is incompatible."
        )
    if value.critical_verification_mismatches:
        titles = {
            "amount": "Amount differs from the stored record",
            "transaction_reference": ("Transaction reference differs from the stored record"),
        }
        reasons = tuple(
            PolicyReason(
                code=f"REFERENCE_{field.upper()}_MISMATCH",
                title=titles[field],
                severity="HIGH",
            )
            for field in policy.critical_verification_fields
            if field in value.critical_verification_mismatches
        )
        return _result(policy, value, RiskBand.HIGH, reasons)
    text_class = value.text_signal.predicted_class
    if value.text_signal.status == "SUCCESS" and text_class == "FRAUDULENT":
        return _result(policy, value, policy.text_class_bands[text_class], ())
    structured_class = value.structured_model.predicted_class
    if value.structured_model.available and structured_class == "FRAUDULENT":
        return _result(policy, value, RiskBand.HIGH, (_structured_reason(structured_class),))
    if (
        value.image_model.available
        and value.image_model.predicted_class == "tampered"
        and value.image_model.score is not None
        and value.image_model.score >= policy.image_high_threshold
    ):
        return _result(
            policy,
            value,
            RiskBand.HIGH,
            (
                PolicyReason(
                    code="IMAGE_MODEL_TAMPER_THRESHOLD_EXCEEDED",
                    title="The accepted image model found manipulation indicators",
                    severity="HIGH",
                ),
            ),
        )
    if value.text_signal.status == "SUCCESS" and text_class == "SUSPICIOUS":
        return _result(policy, value, policy.text_class_bands[text_class], ())
    if value.structured_model.available and structured_class is not None:
        band = policy.structured_class_bands[structured_class]
        if band is RiskBand.LOW and not value.confirmed_critical_fields_complete:
            return _inconclusive(policy, value, "CRITICAL_OCR_FIELDS_INCOMPLETE")
        return _result(policy, value, band, (_structured_reason(structured_class),))
    return _inconclusive(policy, value, "CONCLUSIVE_MODEL_EVIDENCE_UNAVAILABLE")


__all__ = [
    "ANALYSIS_RESULT_CONTRACT_VERSION",
    "AnalysisPolicyInput",
    "AnalysisPolicyResult",
    "FinalizationSemantics",
    "LoadedRiskPolicy",
    "ModelPolicySignal",
    "PolicyFailure",
    "PolicyReason",
    "TextPolicySignal",
    "derive_finalization_semantics",
    "evaluate_risk_policy",
    "load_risk_policy",
]
