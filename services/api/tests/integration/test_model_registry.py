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
from momo_fdvs.services.model_registry import (
    ModelRegistryFailure,
    activate_structured_model,
    active_structured_model,
    predict_with_active_structured_model,
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
