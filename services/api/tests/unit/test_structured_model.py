from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

import joblib
import pandas as pd
import pytest
from flask import Flask
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

from momo_fdvs.models import ModelVersion
from momo_fdvs.services import structured_model
from momo_fdvs.services.structured_model import (
    StructuredModelFailure,
    load_verified_bundle,
    predict_structured,
    resolve_private_artifact,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _schema() -> dict[str, object]:
    return {
        "version": "test-schema-v1",
        "ordered_features": [
            {
                "name": "signal",
                "kind": "numeric",
                "nullable": False,
                "minimum": 0.0,
                "maximum": 1.0,
                "categories": [],
                "description": "Controlled test signal.",
            }
        ],
        "forbidden_features": ["label", "user_id"],
        "classes": ["GENUINE", "SUSPICIOUS", "FRAUDULENT"],
        "risk_scalar_version": "test-risk-v1",
    }


def _schema_hash(schema: dict[str, object]) -> str:
    raw = json.dumps(schema, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _model_and_artifact(
    app: Flask,
    tmp_path: Path,
    *,
    name: str = "controlled-structured",
    version: str = "v1",
    status: str = "ACTIVE",
) -> tuple[ModelVersion, Path]:
    root = tmp_path / "models"
    root.mkdir()
    app.config["STRUCTURED_MODEL_ROOT"] = root
    app.config["STRUCTURED_MODEL_MAX_BYTES"] = 10_000_000
    schema = _schema()
    frame = pd.DataFrame({"signal": [0.0, 0.1, 0.45, 0.55, 0.9, 1.0]})
    labels = ["GENUINE", "GENUINE", "SUSPICIOUS", "SUSPICIOUS", "FRAUDULENT", "FRAUDULENT"]
    pipeline = Pipeline(
        [("classifier", RandomForestClassifier(n_estimators=20, random_state=20260811, n_jobs=1))]
    )
    pipeline.fit(frame, labels)
    path = root / f"{version}.joblib"
    bundle = {
        "artifact_format": "momo-fdvs-trusted-joblib-v1",
        "model_name": name,
        "model_version": version,
        "pipeline": pipeline,
        "classes": ["GENUINE", "SUSPICIOUS", "FRAUDULENT"],
        "feature_names": ["signal"],
        "feature_schema": schema,
        "feature_schema_hash": _schema_hash(schema),
        "feature_schema_version": "test-schema-v1",
        "risk_scalar_version": "test-risk-v1",
        "thresholds": {"suspicious": 0.3, "fraudulent": 0.7},
    }
    joblib.dump(bundle, path, compress=3, protocol=5)
    model = ModelVersion(
        id=uuid.uuid4(),
        model_type="STRUCTURED",
        name=name,
        version=version,
        status=status,
        artifact_uri=f"private://structured/{path.name}",
        artifact_sha256=_sha256(path),
        input_schema_hash=_schema_hash(schema),
        preprocessing_version="test-preprocess-v1",
        framework_versions={},
        metrics={},
    )
    return model, path


def test_verified_active_artifact_produces_complete_prediction(app: Flask, tmp_path: Path) -> None:
    with app.app_context():
        model, _ = _model_and_artifact(app, tmp_path)
        bundle = load_verified_bundle(model)
        assert bundle["model_version"] == "v1"
        result = predict_structured(model, {"signal": 0.95})

    assert result["status"] == "SUCCESS"
    assert result["predicted_class"] in {"GENUINE", "SUSPICIOUS", "FRAUDULENT"}
    assert sum(result["probabilities"].values()) == pytest.approx(1.0)  # type: ignore[union-attr]
    assert result["feature_schema_hash"] == model.input_schema_hash
    assert result["inference_ms"] >= 0  # type: ignore[operator]


def test_hash_mismatch_is_rejected_before_deserialisation(
    app: Flask, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with app.app_context():
        model, path = _model_and_artifact(app, tmp_path)
        path.write_bytes(path.read_bytes() + b"tampered")
        called = False

        def fail_if_called(_path: Path) -> object:
            nonlocal called
            called = True
            raise AssertionError("joblib.load must not run")

        monkeypatch.setattr(structured_model.joblib, "load", fail_if_called)
        with pytest.raises(StructuredModelFailure) as failure:
            load_verified_bundle(model)
        assert failure.value.code == "STRUCTURED_MODEL_HASH_MISMATCH"
        assert called is False


@pytest.mark.parametrize(
    ("row", "code"),
    [
        ({"signal": 0.5, "label": "FRAUDULENT"}, "STRUCTURED_FEATURE_FORBIDDEN"),
        ({}, "STRUCTURED_FEATURE_SCHEMA_MISMATCH"),
        ({"signal": 2.0}, "STRUCTURED_FEATURE_INVALID"),
        ({"signal": True}, "STRUCTURED_FEATURE_INVALID"),
    ],
)
def test_feature_schema_violations_are_explicit(
    app: Flask, tmp_path: Path, row: dict[str, object], code: str
) -> None:
    with app.app_context():
        model, _ = _model_and_artifact(app, tmp_path)
        with pytest.raises(StructuredModelFailure) as failure:
            predict_structured(model, row)
    assert failure.value.code == code


def test_inactive_missing_and_escaping_artifacts_are_unavailable(
    app: Flask, tmp_path: Path
) -> None:
    with app.app_context():
        model, path = _model_and_artifact(app, tmp_path, status="READY")
        with pytest.raises(StructuredModelFailure) as inactive:
            predict_structured(model, {"signal": 0.5})
        assert inactive.value.code == "STRUCTURED_MODEL_NOT_ACTIVE"

        path.unlink()
        with pytest.raises(StructuredModelFailure) as missing:
            load_verified_bundle(model)
        assert missing.value.code == "STRUCTURED_MODEL_ARTIFACT_MISSING"

        with pytest.raises(StructuredModelFailure) as escaping:
            resolve_private_artifact("private://structured/../../outside.joblib")
        assert escaping.value.code == "STRUCTURED_MODEL_URI_INVALID"


def test_registry_and_artifact_schema_or_identity_must_agree(app: Flask, tmp_path: Path) -> None:
    with app.app_context():
        model, _ = _model_and_artifact(app, tmp_path)
        model.input_schema_hash = "0" * 64
        with pytest.raises(StructuredModelFailure) as schema_failure:
            load_verified_bundle(model)
        assert schema_failure.value.code == "STRUCTURED_MODEL_SCHEMA_MISMATCH"

        model.input_schema_hash = _schema_hash(_schema())
        model.version = "different"
        with pytest.raises(StructuredModelFailure) as identity_failure:
            load_verified_bundle(model)
        assert identity_failure.value.code == "STRUCTURED_MODEL_IDENTITY_MISMATCH"
