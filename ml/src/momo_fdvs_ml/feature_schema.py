"""Versioned structured evidence schema with drift and privacy guards."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any, Final

STRUCTURED_FEATURE_SCHEMA_VERSION: Final = "structured-evidence-features-v1"
RISK_SCALAR_VERSION: Final = "p-fraud-plus-half-p-suspicious-v1"
RISK_CLASSES: Final = ("GENUINE", "SUSPICIOUS", "FRAUDULENT")
FORBIDDEN_FEATURE_NAMES: Final = {
    "final_case_decision",
    "final_risk_class",
    "label",
    "name",
    "phone",
    "raw_name",
    "raw_ocr_text",
    "raw_phone",
    "raw_reference",
    "reference",
    "reviewer_decision",
    "user_id",
}


class FeatureSchemaError(ValueError):
    """Raised when a feature row does not match the immutable schema."""


@dataclass(frozen=True)
class FeatureSpec:
    """One ordered input feature and its validation contract."""

    name: str
    kind: str
    nullable: bool = False
    minimum: float | None = None
    maximum: float | None = None
    categories: tuple[str, ...] = ()
    description: str = ""


def _numeric(
    name: str,
    minimum: float,
    maximum: float,
    description: str,
    *,
    nullable: bool = False,
) -> FeatureSpec:
    return FeatureSpec(
        name=name,
        kind="numeric",
        nullable=nullable,
        minimum=minimum,
        maximum=maximum,
        description=description,
    )


def _categorical(name: str, categories: tuple[str, ...], description: str) -> FeatureSpec:
    return FeatureSpec(
        name=name,
        kind="categorical",
        categories=categories,
        description=description,
    )


FEATURE_SPECS: Final[tuple[FeatureSpec, ...]] = (
    _numeric("ocr_required_field_coverage", 0, 1, "Fraction of required fields extracted."),
    _numeric("ocr_mean_confidence", 0, 1, "Mean retained OCR confidence."),
    _numeric("ocr_min_critical_confidence", 0, 1, "Minimum critical-field confidence."),
    _numeric("ocr_provider_confidence", 0, 1, "Provider/template detector confidence."),
    _numeric("critical_correction_count", 0, 20, "Confirmed critical-field corrections."),
    _numeric("total_correction_count", 0, 50, "All confirmed field corrections."),
    _numeric("transaction_reference_valid", 0, 1, "Canonical reference validity flag."),
    _numeric("amount_valid", 0, 1, "Canonical amount validity flag."),
    _numeric("phone_valid", 0, 1, "Canonical phone validity flag."),
    _numeric("timestamp_valid", 0, 1, "Canonical timestamp validity flag."),
    _numeric("status_text_consistent", 0, 1, "Receipt status consistency flag."),
    _numeric("ocr_text_density", 0, 1, "Normalised OCR text density."),
    _numeric("template_anchor_coverage", 0, 1, "Expected template-anchor coverage."),
    _numeric("blur_variance", 0, 100000, "Laplacian sharpness/blur variance."),
    _numeric("contrast_stddev", 0, 255, "Image contrast standard deviation."),
    _numeric("aspect_ratio_deviation", 0, 5, "Deviation from expected aspect ratio."),
    _numeric("crop_proximity", 0, 1, "Proximity of content to image edges."),
    _numeric("metadata_inconsistency_count", 0, 20, "Contextual metadata inconsistency count."),
    _numeric("ela_mean", 0, 255, "Controlled recompression residual mean."),
    _numeric("ela_p95", 0, 255, "Controlled recompression residual 95th percentile."),
    _numeric("noise_regional_cv", 0, 10, "Regional residual coefficient of variation."),
    _numeric("text_baseline_deviation", 0, 2, "OCR baseline deviation proxy."),
    _numeric("text_size_cv", 0, 10, "OCR text-size coefficient of variation."),
    _numeric("exact_duplicate_count", 0, 1000, "Privacy-safe exact duplicate count."),
    _numeric(
        "nearest_phash_distance",
        0,
        64,
        "Nearest perceptual-hash distance.",
        nullable=True,
    ),
    _numeric(
        "cnn_tamper_probability",
        0,
        1,
        "Image-model probability when available.",
        nullable=True,
    ),
    _numeric("cnn_available", 0, 1, "Image-model availability flag."),
    _numeric("reference_candidate_found", 0, 1, "Stored-reference candidate found flag."),
    _numeric("amount_match", 0, 1, "Stored-reference amount comparison.", nullable=True),
    _numeric("currency_match", 0, 1, "Stored-reference currency comparison.", nullable=True),
    _numeric("phone_match", 0, 1, "Stored-reference phone comparison.", nullable=True),
    _numeric("name_similarity", 0, 1, "Normalised recipient-name similarity.", nullable=True),
    _numeric(
        "timestamp_difference_minutes",
        0,
        525600,
        "Absolute stored-reference timestamp difference.",
        nullable=True,
    ),
    _numeric(
        "reference_status_match",
        0,
        1,
        "Stored-reference status comparison.",
        nullable=True,
    ),
    _numeric("verification_mismatch_count", 0, 10, "Critical verification mismatch count."),
    _numeric("reused_reference_count", 0, 1000, "Reference reuse count before this event."),
    _numeric("nearest_phash_missing", 0, 1, "Explicit perceptual-distance missingness."),
    _numeric("cnn_probability_missing", 0, 1, "Explicit CNN probability missingness."),
    _numeric("reference_comparison_missing", 0, 1, "Explicit verification missingness."),
    _numeric("name_similarity_missing", 0, 1, "Explicit name-comparison missingness."),
    _numeric("timestamp_difference_missing", 0, 1, "Explicit timestamp-comparison missingness."),
    _categorical(
        "provider_code",
        ("GENERIC_MOMO", "UNKNOWN", "OTHER_AUTHORISED"),
        "Non-identifying provider/template scope.",
    ),
    _categorical(
        "template_code",
        ("GENERIC_V1", "UNKNOWN", "OTHER_AUTHORISED"),
        "Versioned template family.",
    ),
    _categorical(
        "verification_status",
        ("VERIFIED", "UNVERIFIED", "MISMATCH"),
        "Stored/imported reference verification status.",
    ),
    _categorical(
        "image_evidence_status",
        ("AVAILABLE", "PARTIAL", "UNAVAILABLE"),
        "Deterministic image-evidence availability.",
    ),
    _categorical(
        "ocr_engine_status",
        ("AVAILABLE", "DEGRADED", "UNAVAILABLE"),
        "OCR engine/evidence availability.",
    ),
)

FEATURE_NAMES: Final = tuple(spec.name for spec in FEATURE_SPECS)
NUMERIC_FEATURE_NAMES: Final = tuple(spec.name for spec in FEATURE_SPECS if spec.kind == "numeric")
CATEGORICAL_FEATURE_NAMES: Final = tuple(
    spec.name for spec in FEATURE_SPECS if spec.kind == "categorical"
)


def feature_schema_payload() -> dict[str, Any]:
    """Return the canonical schema embedded in trusted artifacts."""

    return {
        "version": STRUCTURED_FEATURE_SCHEMA_VERSION,
        "ordered_features": [asdict(spec) for spec in FEATURE_SPECS],
        "forbidden_features": sorted(FORBIDDEN_FEATURE_NAMES),
        "classes": list(RISK_CLASSES),
        "risk_scalar_version": RISK_SCALAR_VERSION,
    }


def feature_schema_hash(payload: Mapping[str, Any] | None = None) -> str:
    """Hash the exact schema ordering, ranges, categories and forbidden fields."""

    raw = json.dumps(
        feature_schema_payload() if payload is None else payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


STRUCTURED_FEATURE_SCHEMA_HASH: Final = feature_schema_hash()


def validate_feature_row(row: Mapping[str, object]) -> dict[str, object]:
    """Reject schema drift, unsafe fields and invalid values; preserve explicit nulls."""

    supplied = set(row)
    forbidden = sorted(supplied & FORBIDDEN_FEATURE_NAMES)
    if forbidden:
        raise FeatureSchemaError(f"forbidden feature(s): {', '.join(forbidden)}")
    missing = sorted(set(FEATURE_NAMES) - supplied)
    extra = sorted(supplied - set(FEATURE_NAMES))
    if missing:
        raise FeatureSchemaError(f"missing feature(s): {', '.join(missing)}")
    if extra:
        raise FeatureSchemaError(f"unknown feature(s): {', '.join(extra)}")

    normalised: dict[str, object] = {}
    for spec in FEATURE_SPECS:
        value = row[spec.name]
        if value is None:
            if not spec.nullable:
                raise FeatureSchemaError(f"{spec.name} cannot be null")
            normalised[spec.name] = None
            continue
        if spec.kind == "categorical":
            if not isinstance(value, str) or value not in spec.categories:
                raise FeatureSchemaError(f"{spec.name} must be one of {', '.join(spec.categories)}")
            normalised[spec.name] = value
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise FeatureSchemaError(f"{spec.name} must be numeric")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise FeatureSchemaError(f"{spec.name} must be finite")
        if spec.minimum is not None and numeric < spec.minimum:
            raise FeatureSchemaError(f"{spec.name} is below {spec.minimum}")
        if spec.maximum is not None and numeric > spec.maximum:
            raise FeatureSchemaError(f"{spec.name} is above {spec.maximum}")
        normalised[spec.name] = numeric
    return normalised


def calculate_risk_scalar(probabilities: Mapping[str, float]) -> float:
    """Transform the full class vector into the stored scalar ML component."""

    if set(probabilities) != set(RISK_CLASSES):
        raise FeatureSchemaError("probability vector must contain exactly three risk classes")
    values = {key: float(value) for key, value in probabilities.items()}
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in values.values()):
        raise FeatureSchemaError("probabilities must be finite values in [0, 1]")
    if not math.isclose(sum(values.values()), 1.0, rel_tol=1e-6, abs_tol=1e-6):
        raise FeatureSchemaError("probabilities must sum to one")
    return max(0.0, min(1.0, values["FRAUDULENT"] + 0.5 * values["SUSPICIOUS"]))


def classify_risk_scalar(
    risk_scalar: float, *, suspicious_threshold: float, fraudulent_threshold: float
) -> str:
    """Classify a validated scalar using validation-selected ordered thresholds."""

    if not 0 <= suspicious_threshold < fraudulent_threshold <= 1:
        raise FeatureSchemaError("thresholds must satisfy 0 <= suspicious < fraudulent <= 1")
    if not math.isfinite(risk_scalar) or not 0 <= risk_scalar <= 1:
        raise FeatureSchemaError("risk scalar must be finite and in [0, 1]")
    if risk_scalar >= fraudulent_threshold:
        return "FRAUDULENT"
    if risk_scalar >= suspicious_threshold:
        return "SUSPICIOUS"
    return "GENUINE"
