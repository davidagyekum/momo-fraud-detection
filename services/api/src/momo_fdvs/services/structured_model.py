"""Trusted structured-model artifact loading and deterministic inference."""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final, cast
from urllib.parse import urlparse

import joblib
import numpy as np
import pandas as pd
from flask import current_app
from sklearn.pipeline import Pipeline

from momo_fdvs.models import ModelVersion

ARTIFACT_FORMAT: Final = "momo-fdvs-trusted-joblib-v1"
RISK_CLASSES: Final = ("GENUINE", "SUSPICIOUS", "FRAUDULENT")
SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")


class StructuredModelFailure(RuntimeError):
    """A safe, machine-readable structured-model failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_private_artifact(artifact_uri: str) -> Path:
    """Resolve a registry URI beneath the private structured-model root."""

    parsed = urlparse(artifact_uri)
    if parsed.scheme != "private" or parsed.netloc != "structured":
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_URI_INVALID",
            "The structured model artifact URI is not supported.",
        )
    relative = parsed.path.lstrip("/")
    if not relative:
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_URI_INVALID", "The structured model artifact URI is empty."
        )
    root = Path(current_app.config["STRUCTURED_MODEL_ROOT"]).resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root):
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_URI_INVALID",
            "The structured model artifact URI escapes its private root.",
        )
    if not candidate.is_file():
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_ARTIFACT_MISSING",
            "The registered structured model artifact is unavailable.",
        )
    if candidate.stat().st_size > int(current_app.config["STRUCTURED_MODEL_MAX_BYTES"]):
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_ARTIFACT_TOO_LARGE",
            "The registered structured model artifact exceeds the configured limit.",
        )
    return candidate


def _schema_hash(schema: Mapping[str, object]) -> str:
    raw = json.dumps(schema, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def load_verified_bundle(model: ModelVersion) -> dict[str, Any]:
    """Verify registry metadata and bytes before trusted joblib deserialisation."""

    if model.model_type != "STRUCTURED":
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_TYPE_INVALID", "The registered model is not structured."
        )
    if not SHA256_PATTERN.fullmatch(model.artifact_sha256):
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_HASH_INVALID", "The registered artifact hash is invalid."
        )
    path = resolve_private_artifact(model.artifact_uri)
    if _sha256_file(path) != model.artifact_sha256:
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_HASH_MISMATCH",
            "The structured model artifact failed integrity verification.",
        )

    try:
        loaded = joblib.load(path)
    except Exception as exc:
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_DESERIALISATION_FAILED",
            "The verified structured model artifact could not be loaded.",
        ) from exc
    if not isinstance(loaded, dict) or loaded.get("artifact_format") != ARTIFACT_FORMAT:
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_FORMAT_INVALID", "The structured model artifact is unsupported."
        )
    bundle = cast(dict[str, Any], loaded)
    schema = bundle.get("feature_schema")
    if not isinstance(schema, dict):
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_SCHEMA_INVALID", "The artifact feature schema is missing."
        )
    actual_schema_hash = _schema_hash(schema)
    if actual_schema_hash != model.input_schema_hash or actual_schema_hash != bundle.get(
        "feature_schema_hash"
    ):
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_SCHEMA_MISMATCH",
            "The artifact feature schema does not match the registry.",
        )
    if bundle.get("model_name") != model.name or bundle.get("model_version") != model.version:
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_IDENTITY_MISMATCH",
            "The artifact identity does not match the registry.",
        )
    if bundle.get("classes") != list(RISK_CLASSES):
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_CLASSES_INVALID",
            "The artifact risk-class ordering is invalid.",
        )
    ordered = schema.get("ordered_features")
    if not isinstance(ordered, list) or bundle.get("feature_names") != [
        item.get("name") for item in ordered if isinstance(item, dict)
    ]:
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_FEATURE_ORDER_INVALID",
            "The artifact feature ordering is invalid.",
        )
    return bundle


def _validate_feature_row(
    bundle: Mapping[str, Any], row: Mapping[str, object]
) -> tuple[dict[str, object], list[str]]:
    schema = cast(Mapping[str, Any], bundle["feature_schema"])
    specs = schema.get("ordered_features")
    forbidden = schema.get("forbidden_features")
    if not isinstance(specs, list) or not isinstance(forbidden, list):
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_SCHEMA_INVALID", "The artifact feature schema is malformed."
        )
    names = [item.get("name") for item in specs if isinstance(item, dict)]
    if len(names) != len(specs) or any(not isinstance(name, str) for name in names):
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_SCHEMA_INVALID", "The artifact feature schema is malformed."
        )
    validated_names = cast(list[str], names)
    supplied = set(row)
    prohibited = sorted(supplied & set(forbidden))
    missing = sorted(set(validated_names) - supplied)
    extra = sorted(supplied - set(validated_names))
    if prohibited:
        raise StructuredModelFailure(
            "STRUCTURED_FEATURE_FORBIDDEN", f"Forbidden features: {', '.join(prohibited)}."
        )
    if missing or extra:
        raise StructuredModelFailure(
            "STRUCTURED_FEATURE_SCHEMA_MISMATCH",
            "Structured features do not match the active model schema.",
        )

    normalised: dict[str, object] = {}
    for item in specs:
        spec = cast(Mapping[str, Any], item)
        name = cast(str, spec["name"])
        value = row[name]
        if value is None:
            if not bool(spec.get("nullable")):
                raise StructuredModelFailure(
                    "STRUCTURED_FEATURE_INVALID", f"{name} cannot be null."
                )
            normalised[name] = None
            continue
        if spec.get("kind") == "categorical":
            categories = spec.get("categories")
            if (
                not isinstance(value, str)
                or not isinstance(categories, list)
                or value not in categories
            ):
                raise StructuredModelFailure(
                    "STRUCTURED_FEATURE_INVALID", f"{name} has an invalid category."
                )
            normalised[name] = value
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise StructuredModelFailure("STRUCTURED_FEATURE_INVALID", f"{name} must be numeric.")
        numeric = float(value)
        minimum = spec.get("minimum")
        maximum = spec.get("maximum")
        if (
            not math.isfinite(numeric)
            or (minimum is not None and numeric < float(minimum))
            or (maximum is not None and numeric > float(maximum))
        ):
            raise StructuredModelFailure(
                "STRUCTURED_FEATURE_INVALID", f"{name} is outside its valid range."
            )
        normalised[name] = numeric
    return normalised, validated_names


def predict_structured(model: ModelVersion, feature_row: Mapping[str, object]) -> dict[str, object]:
    """Produce a probability vector and class from one verified active model."""

    if model.status != "ACTIVE":
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_NOT_ACTIVE", "No active structured model is available."
        )
    started = time.perf_counter()
    bundle = load_verified_bundle(model)
    normalised, names = _validate_feature_row(bundle, feature_row)
    pipeline = bundle.get("pipeline")
    if not isinstance(pipeline, Pipeline):
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_PIPELINE_INVALID", "The artifact pipeline is invalid."
        )
    raw = cast(np.ndarray, pipeline.predict_proba(pd.DataFrame([normalised], columns=names)))
    classes = tuple(str(value) for value in pipeline.classes_)
    if set(classes) != set(RISK_CLASSES) or raw.shape != (1, 3):
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_OUTPUT_INVALID", "The model returned an invalid probability vector."
        )
    probabilities = {label: float(raw[0, classes.index(label)]) for label in RISK_CLASSES}
    total = sum(probabilities.values())
    if not math.isfinite(total) or total <= 0:
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_OUTPUT_INVALID", "The model returned invalid probability mass."
        )
    probabilities = {label: value / total for label, value in probabilities.items()}
    risk_scalar = probabilities["FRAUDULENT"] + 0.5 * probabilities["SUSPICIOUS"]
    thresholds = bundle.get("thresholds")
    if not isinstance(thresholds, dict):
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_THRESHOLD_INVALID", "The artifact thresholds are invalid."
        )
    suspicious = float(thresholds.get("suspicious", -1))
    fraudulent = float(thresholds.get("fraudulent", -1))
    if not 0 <= suspicious < fraudulent <= 1:
        raise StructuredModelFailure(
            "STRUCTURED_MODEL_THRESHOLD_INVALID", "The artifact thresholds are invalid."
        )
    predicted = (
        "FRAUDULENT"
        if risk_scalar >= fraudulent
        else "SUSPICIOUS"
        if risk_scalar >= suspicious
        else "GENUINE"
    )
    return {
        "status": "SUCCESS",
        "model_version_id": str(model.id),
        "model_name": model.name,
        "model_version": model.version,
        "predicted_class": predicted,
        "probabilities": {key: round(value, 8) for key, value in probabilities.items()},
        "risk_scalar": round(risk_scalar, 8),
        "risk_scalar_version": bundle.get("risk_scalar_version"),
        "feature_schema_hash": model.input_schema_hash,
        "feature_schema_version": bundle.get("feature_schema_version"),
        "thresholds": {"suspicious": suspicious, "fraudulent": fraudulent},
        "inference_ms": max(0, round((time.perf_counter() - started) * 1000)),
    }
