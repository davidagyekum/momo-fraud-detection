from __future__ import annotations

import math

import pytest

from momo_fdvs_ml.feature_schema import (
    FEATURE_NAMES,
    RISK_CLASSES,
    STRUCTURED_FEATURE_SCHEMA_HASH,
    FeatureSchemaError,
    calculate_risk_scalar,
    classify_risk_scalar,
    feature_schema_hash,
    feature_schema_payload,
    validate_feature_row,
)
from momo_fdvs_ml.manifest import load_manifest
from momo_fdvs_ml.structured_dataset import generate_controlled_structured_rows


def _valid_row():  # type: ignore[no-untyped-def]
    manifest = load_manifest(
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "data"
        / "controlled"
        / "manifest.csv"
    )
    return {name: generate_controlled_structured_rows(manifest)[0][name] for name in FEATURE_NAMES}


def test_schema_hash_covers_order_ranges_categories_and_forbidden_fields() -> None:
    payload = feature_schema_payload()

    assert len(FEATURE_NAMES) == 46
    assert len(STRUCTURED_FEATURE_SCHEMA_HASH) == 64
    assert feature_schema_hash(payload) == STRUCTURED_FEATURE_SCHEMA_HASH
    modified = dict(payload)
    modified["version"] = "drifted"
    assert feature_schema_hash(modified) != STRUCTURED_FEATURE_SCHEMA_HASH


def test_feature_row_validation_preserves_explicit_nulls() -> None:
    row = _valid_row()
    normalised = validate_feature_row(row)

    assert tuple(normalised) == FEATURE_NAMES
    assert normalised["cnn_tamper_probability"] is None


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda row: row.pop("amount_valid"), "missing feature"),
        (lambda row: row.update({"unknown": 1}), "unknown feature"),
        (lambda row: row.update({"raw_phone": "0240000000"}), "forbidden feature"),
        (lambda row: row.update({"amount_valid": 2}), "above"),
        (lambda row: row.update({"provider_code": "REAL_PROVIDER"}), "must be one of"),
        (lambda row: row.update({"amount_valid": True}), "must be numeric"),
        (lambda row: row.update({"amount_valid": math.inf}), "finite"),
        (lambda row: row.update({"amount_valid": None}), "cannot be null"),
    ],
)
def test_feature_row_rejects_drift_and_invalid_values(mutation, message: str) -> None:  # type: ignore[no-untyped-def]
    row = _valid_row()
    mutation(row)
    with pytest.raises(FeatureSchemaError, match=message):
        validate_feature_row(row)


def test_risk_scalar_and_threshold_classification() -> None:
    probabilities = {"GENUINE": 0.2, "SUSPICIOUS": 0.4, "FRAUDULENT": 0.4}
    scalar = calculate_risk_scalar(probabilities)

    assert scalar == pytest.approx(0.6)
    assert (
        classify_risk_scalar(scalar, suspicious_threshold=0.3, fraudulent_threshold=0.7)
        == "SUSPICIOUS"
    )
    assert (
        classify_risk_scalar(0.2, suspicious_threshold=0.3, fraudulent_threshold=0.7) == "GENUINE"
    )
    assert (
        classify_risk_scalar(0.8, suspicious_threshold=0.3, fraudulent_threshold=0.7)
        == "FRAUDULENT"
    )


@pytest.mark.parametrize(
    "probabilities",
    [
        {"GENUINE": 0.5, "SUSPICIOUS": 0.5},
        {"GENUINE": 0.8, "SUSPICIOUS": 0.3, "FRAUDULENT": 0.1},
        {"GENUINE": -0.1, "SUSPICIOUS": 0.5, "FRAUDULENT": 0.6},
    ],
)
def test_risk_scalar_rejects_invalid_vectors(probabilities) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(FeatureSchemaError):
        calculate_risk_scalar(probabilities)


def test_thresholds_must_be_ordered() -> None:
    with pytest.raises(FeatureSchemaError, match="thresholds"):
        classify_risk_scalar(0.5, suspicious_threshold=0.8, fraudulent_threshold=0.7)
    with pytest.raises(FeatureSchemaError, match="risk scalar"):
        classify_risk_scalar(math.nan, suspicious_threshold=0.3, fraudulent_threshold=0.7)


def test_risk_classes_are_fixed_and_ordered() -> None:
    assert RISK_CLASSES == ("GENUINE", "SUSPICIOUS", "FRAUDULENT")
