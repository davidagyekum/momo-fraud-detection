from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd
import pytest
from flask import Flask
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sqlalchemy import select

from momo_fdvs.extensions import db
from momo_fdvs.models import AuditLog, Role, User, UserRole
from momo_fdvs.services import model_registry
from momo_fdvs.services.image_model import (
    IMAGE_PREPROCESSING_SCHEMA_HASH,
    IMAGE_PREPROCESSING_VERSION,
    ImageModelFailure,
)
from momo_fdvs.services.model_registry import (
    ModelRegistryFailure,
    activate_image_model,
    activate_structured_model,
    active_image_model,
    active_structured_model,
    predict_with_active_image_model,
    predict_with_active_structured_model,
    register_image_model,
    register_structured_model,
)

pytestmark = pytest.mark.skipif(
    not (os.getenv("TEST_DATABASE_URL") or os.getenv("P02_TEST_DATABASE_URL")),
    reason="requires an isolated PostgreSQL test database",
)


def _schema() -> dict[str, object]:
    return {
        "version": "registry-test-v1",
        "ordered_features": [
            {
                "name": "signal",
                "kind": "numeric",
                "nullable": False,
                "minimum": 0.0,
                "maximum": 1.0,
                "categories": [],
                "description": "Controlled registry test signal.",
            }
        ],
        "forbidden_features": ["label"],
        "classes": ["GENUINE", "SUSPICIOUS", "FRAUDULENT"],
        "risk_scalar_version": "registry-risk-v1",
    }


def _hash_json(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _payload(root: Path, version: str, *, accepted: bool = True) -> dict[str, object]:
    schema = _schema()
    name = "registry-controlled-model"
    frame = pd.DataFrame({"signal": [0.0, 0.1, 0.5, 0.6, 0.9, 1.0]})
    labels = ["GENUINE", "GENUINE", "SUSPICIOUS", "SUSPICIOUS", "FRAUDULENT", "FRAUDULENT"]
    pipeline = Pipeline(
        [("classifier", RandomForestClassifier(n_estimators=20, random_state=7, n_jobs=1))]
    )
    pipeline.fit(frame, labels)
    artifact = root / f"{version}.joblib"
    joblib.dump(
        {
            "artifact_format": "momo-fdvs-trusted-joblib-v1",
            "model_name": name,
            "model_version": version,
            "pipeline": pipeline,
            "classes": ["GENUINE", "SUSPICIOUS", "FRAUDULENT"],
            "feature_names": ["signal"],
            "feature_schema": schema,
            "feature_schema_hash": _hash_json(schema),
            "feature_schema_version": "registry-test-v1",
            "risk_scalar_version": "registry-risk-v1",
            "thresholds": {"suspicious": 0.3, "fraudulent": 0.7},
        },
        artifact,
        compress=3,
        protocol=5,
    )
    return {
        "model_type": "STRUCTURED",
        "name": name,
        "version": version,
        "artifact_uri": f"private://structured/{artifact.name}",
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "input_schema_hash": _hash_json(schema),
        "preprocessing_version": "registry-preprocess-v1",
        "framework_versions": {"scikit_learn": "test"},
        "metrics": {"acceptance_passed": accepted, "scope": "controlled_test"},
        "dataset_manifest_hash": "1" * 64,
        "split_hash": "2" * 64,
        "training_commit_sha": "3" * 40,
        "model_card_key": "docs/models/test.md",
    }


def _admin() -> User:
    suffix = uuid.uuid4()
    if db.session.get(Role, "ADMIN") is None:
        db.session.add(Role(code="ADMIN", description="Administrator"))
    actor = User(
        email=f"model-admin-{suffix}@example.test",
        password_hash="fixture-only",
        full_name="Model Administrator",
        status="ACTIVE",
        password_changed_at=datetime.now(UTC),
    )
    db.session.add(actor)
    db.session.flush()
    db.session.add(
        UserRole(
            user_id=actor.id,
            role_code="ADMIN",
            granted_by=actor.id,
            granted_at=datetime.now(UTC),
        )
    )
    db.session.commit()
    return actor


def test_admin_registration_activation_replacement_and_rollback(app: Flask, tmp_path: Path) -> None:
    root = tmp_path / "structured"
    root.mkdir()
    app.config["STRUCTURED_MODEL_ROOT"] = root
    with app.app_context():
        actor = _admin()
        first = register_structured_model(_payload(root, f"v1-{uuid.uuid4()}"), actor, {"ADMIN"})
        assert first.status == "READY"
        with pytest.raises(ModelRegistryFailure) as confirmation:
            activate_structured_model(first.id, actor, {"ADMIN"}, confirmed=False)
        assert confirmation.value.code == "MODEL_ACTIVATION_CONFIRMATION_REQUIRED"

        activate_structured_model(first.id, actor, {"ADMIN"}, confirmed=True)
        second = register_structured_model(_payload(root, f"v2-{uuid.uuid4()}"), actor, {"ADMIN"})
        activate_structured_model(second.id, actor, {"ADMIN"}, confirmed=True)
        db.session.refresh(first)
        assert first.status == "RETIRED"
        assert active_structured_model(first.name).id == second.id  # type: ignore[union-attr]

        activate_structured_model(first.id, actor, {"ADMIN"}, confirmed=True, rollback=True)
        db.session.refresh(second)
        assert second.status == "RETIRED"
        assert active_structured_model(first.name).id == first.id  # type: ignore[union-attr]
        actions = set(
            db.session.scalars(
                select(AuditLog.action).where(AuditLog.target_type == "model_version")
            ).all()
        )
        assert {
            "model.structured_registered",
            "model.structured_activated",
            "model.structured_rollback",
        } <= actions


def test_rejected_metrics_and_non_admin_cannot_activate(app: Flask, tmp_path: Path) -> None:
    root = tmp_path / "structured"
    root.mkdir()
    app.config["STRUCTURED_MODEL_ROOT"] = root
    with app.app_context():
        actor = _admin()
        failed = register_structured_model(
            _payload(root, f"failed-{uuid.uuid4()}", accepted=False), actor, {"ADMIN"}
        )
        assert failed.status == "FAILED"
        with pytest.raises(ModelRegistryFailure) as invalid_status:
            activate_structured_model(failed.id, actor, {"ADMIN"}, confirmed=True)
        assert invalid_status.value.code == "MODEL_STATUS_INVALID"
        with pytest.raises(ModelRegistryFailure) as forbidden:
            register_structured_model(_payload(root, f"forbidden-{uuid.uuid4()}"), actor, {"USER"})
        assert forbidden.value.code == "MODEL_REGISTRY_FORBIDDEN"


def test_missing_active_model_returns_explicit_unavailable(app: Flask) -> None:
    with app.app_context():
        result = predict_with_active_structured_model(f"absent-{uuid.uuid4()}", {"signal": 0.5})
    assert result == {
        "status": "UNAVAILABLE",
        "error_code": "STRUCTURED_MODEL_NOT_ACTIVE",
        "predicted_class": None,
        "probabilities": {},
    }


def _image_payload(version: str, *, accepted: bool = True) -> dict[str, object]:
    return {
        "model_type": "IMAGE",
        "name": "registry-controlled-image",
        "version": version,
        "artifact_uri": f"private://image/{version}.keras",
        "artifact_sha256": "a" * 64,
        "input_schema_hash": IMAGE_PREPROCESSING_SCHEMA_HASH,
        "preprocessing_version": IMAGE_PREPROCESSING_VERSION,
        "framework_versions": {"tensorflow": "2.21.0-test"},
        "metrics": {
            "acceptance_passed": accepted,
            "scope": "controlled_test",
            "threshold": 0.5,
        },
        "dataset_manifest_hash": "1" * 64,
        "split_hash": "2" * 64,
        "training_commit_sha": "3" * 40,
        "model_card_key": "docs/models/image-test.md",
    }


def test_image_registration_activation_rollback_and_unavailable_state(
    app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(model_registry, "load_verified_image_model", lambda model: object())
    with app.app_context():
        actor = _admin()
        first = register_image_model(_image_payload(f"v1-{uuid.uuid4()}"), actor, {"ADMIN"})
        assert first.status == "READY"
        with pytest.raises(ModelRegistryFailure) as confirmation:
            activate_image_model(first.id, actor, {"ADMIN"}, confirmed=False)
        assert confirmation.value.code == "MODEL_ACTIVATION_CONFIRMATION_REQUIRED"
        activate_image_model(first.id, actor, {"ADMIN"}, confirmed=True)

        second = register_image_model(_image_payload(f"v2-{uuid.uuid4()}"), actor, {"ADMIN"})
        activate_image_model(second.id, actor, {"ADMIN"}, confirmed=True)
        db.session.refresh(first)
        assert first.status == "RETIRED"
        assert active_image_model(first.name).id == second.id  # type: ignore[union-attr]

        activate_image_model(first.id, actor, {"ADMIN"}, confirmed=True, rollback=True)
        db.session.refresh(second)
        assert second.status == "RETIRED"
        assert active_image_model(first.name).id == first.id  # type: ignore[union-attr]
        monkeypatch.setattr(
            model_registry,
            "predict_image_tampering",
            lambda model, payload: {"status": "SUCCESS", "tamper_probability": 0.25},
        )
        assert predict_with_active_image_model(first.name, b"image")["status"] == "SUCCESS"
        actions = set(
            db.session.scalars(
                select(AuditLog.action).where(AuditLog.target_type == "model_version")
            ).all()
        )
        assert {
            "model.image_registered",
            "model.image_activated",
            "model.image_rollback",
        } <= actions

        failed = register_image_model(
            _image_payload(f"failed-{uuid.uuid4()}", accepted=False), actor, {"ADMIN"}
        )
        assert failed.status == "FAILED"
        with pytest.raises(ModelRegistryFailure) as status:
            activate_image_model(failed.id, actor, {"ADMIN"}, confirmed=True)
        assert status.value.code == "MODEL_STATUS_INVALID"
        with pytest.raises(ModelRegistryFailure) as forbidden:
            register_image_model(_image_payload(f"forbidden-{uuid.uuid4()}"), actor, {"USER"})
        assert forbidden.value.code == "MODEL_REGISTRY_FORBIDDEN"


def test_image_prediction_explicit_unavailable_and_error(
    app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    with app.app_context():
        absent = predict_with_active_image_model(f"absent-{uuid.uuid4()}", b"image")
        assert absent == {
            "status": "UNAVAILABLE",
            "error_code": "IMAGE_MODEL_NOT_ACTIVE",
            "tamper_probability": None,
            "predicted_class": None,
        }
        actor = _admin()
        monkeypatch.setattr(model_registry, "load_verified_image_model", lambda model: object())
        active = register_image_model(_image_payload(f"error-{uuid.uuid4()}"), actor, {"ADMIN"})
        activate_image_model(active.id, actor, {"ADMIN"}, confirmed=True)

        def fail(model: object, payload: bytes) -> dict[str, object]:
            raise ImageModelFailure("IMAGE_MODEL_INFERENCE_FAILED", "controlled failure")

        monkeypatch.setattr(model_registry, "predict_image_tampering", fail)
        result = predict_with_active_image_model(active.name, b"image")
        assert result["status"] == "ERROR"
        assert result["error_code"] == "IMAGE_MODEL_INFERENCE_FAILED"
        assert result["tamper_probability"] is None
