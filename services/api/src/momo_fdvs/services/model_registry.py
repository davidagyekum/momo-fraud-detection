"""Governed structured-model registration, activation and rollback."""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from momo_fdvs.extensions import db
from momo_fdvs.models import ModelVersion, User
from momo_fdvs.services.audit import audit_event
from momo_fdvs.services.structured_model import (
    StructuredModelFailure,
    load_verified_bundle,
    predict_structured,
)

SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")


class ModelRegistryFailure(RuntimeError):
    """A safe, machine-readable model-governance failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _require_admin(actor: User, roles: set[str]) -> None:
    if actor.status != "ACTIVE" or "ADMIN" not in roles:
        raise ModelRegistryFailure(
            "MODEL_REGISTRY_FORBIDDEN", "An active administrator is required."
        )


def _required_text(payload: dict[str, Any], name: str, maximum: int) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ModelRegistryFailure("MODEL_REGISTRY_PAYLOAD_INVALID", f"{name} is invalid.")
    return value.strip()


def register_structured_model(
    payload: dict[str, Any], actor: User, roles: set[str]
) -> ModelVersion:
    """Register one artifact as READY/FAILED after local integrity verification."""

    _require_admin(actor, roles)
    if payload.get("model_type") != "STRUCTURED":
        raise ModelRegistryFailure(
            "MODEL_REGISTRY_PAYLOAD_INVALID", "model_type must be STRUCTURED."
        )
    artifact_sha = _required_text(payload, "artifact_sha256", 64)
    schema_hash = _required_text(payload, "input_schema_hash", 64)
    commit_sha = _required_text(payload, "training_commit_sha", 40)
    if (
        not SHA256_PATTERN.fullmatch(artifact_sha)
        or not SHA256_PATTERN.fullmatch(schema_hash)
        or not COMMIT_PATTERN.fullmatch(commit_sha)
    ):
        raise ModelRegistryFailure(
            "MODEL_REGISTRY_PAYLOAD_INVALID", "A registry hash or commit SHA is invalid."
        )
    metrics = payload.get("metrics")
    frameworks = payload.get("framework_versions")
    if not isinstance(metrics, dict) or not isinstance(frameworks, dict):
        raise ModelRegistryFailure(
            "MODEL_REGISTRY_PAYLOAD_INVALID", "Metrics and framework versions are required."
        )
    status = "READY" if metrics.get("acceptance_passed") is True else "FAILED"
    model = ModelVersion(
        model_type="STRUCTURED",
        name=_required_text(payload, "name", 150),
        version=_required_text(payload, "version", 100),
        status=status,
        artifact_uri=_required_text(payload, "artifact_uri", 1000),
        artifact_sha256=artifact_sha,
        input_schema_hash=schema_hash,
        preprocessing_version=_required_text(payload, "preprocessing_version", 100),
        framework_versions=frameworks,
        metrics=metrics,
        dataset_manifest_hash=payload.get("dataset_manifest_hash"),
        split_hash=payload.get("split_hash"),
        training_commit_sha=commit_sha,
        model_card_key=payload.get("model_card_key"),
        created_by=actor.id,
    )
    db.session.add(model)
    db.session.flush()
    try:
        load_verified_bundle(model)
    except StructuredModelFailure as exc:
        db.session.rollback()
        raise ModelRegistryFailure(exc.code, str(exc)) from exc
    audit_event(
        "model.structured_registered",
        "SUCCESS",
        actor_id=actor.id,
        roles=roles,
        target_type="model_version",
        target_id=model.id,
        metadata={"name": model.name, "version": model.version, "status": model.status},
    )
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ModelRegistryFailure(
            "MODEL_VERSION_CONFLICT", "That structured model version is already registered."
        ) from exc
    return model


def active_structured_model(name: str) -> ModelVersion | None:
    return db.session.scalar(
        select(ModelVersion).where(
            ModelVersion.model_type == "STRUCTURED",
            ModelVersion.name == name,
            ModelVersion.status == "ACTIVE",
        )
    )


def predict_with_active_structured_model(
    name: str, feature_row: Mapping[str, object]
) -> dict[str, object]:
    """Return an explicit unavailable/error state instead of implying model success."""

    model = active_structured_model(name)
    if model is None:
        return {
            "status": "UNAVAILABLE",
            "error_code": "STRUCTURED_MODEL_NOT_ACTIVE",
            "predicted_class": None,
            "probabilities": {},
        }
    try:
        return predict_structured(model, feature_row)
    except StructuredModelFailure as exc:
        return {
            "status": "ERROR",
            "error_code": exc.code,
            "predicted_class": None,
            "probabilities": {},
            "model_version_id": str(model.id),
        }


def activate_structured_model(
    model_id: uuid.UUID,
    actor: User,
    roles: set[str],
    *,
    confirmed: bool,
    rollback: bool = False,
) -> ModelVersion:
    """Explicitly activate READY or rollback to RETIRED after re-verification."""

    _require_admin(actor, roles)
    if not confirmed:
        raise ModelRegistryFailure(
            "MODEL_ACTIVATION_CONFIRMATION_REQUIRED",
            "Explicit model activation confirmation is required.",
        )
    model = db.session.get(ModelVersion, model_id)
    allowed = {"RETIRED"} if rollback else {"READY"}
    if model is None or model.model_type != "STRUCTURED":
        raise ModelRegistryFailure("MODEL_VERSION_NOT_FOUND", "The model version was not found.")
    if model.status not in allowed:
        raise ModelRegistryFailure(
            "MODEL_STATUS_INVALID", "The model version is not eligible for this activation."
        )
    load_verified_bundle(model)
    current = active_structured_model(model.name)
    now = datetime.now(UTC)
    if current is not None:
        current.status = "RETIRED"
        # Flush the retirement first so PostgreSQL's partial unique index never
        # observes two ACTIVE versions during SQLAlchemy's update ordering.
        db.session.flush()
    model.status = "ACTIVE"
    model.activated_by = actor.id
    model.activated_at = now
    audit_event(
        "model.structured_rollback" if rollback else "model.structured_activated",
        "SUCCESS",
        actor_id=actor.id,
        roles=roles,
        target_type="model_version",
        target_id=model.id,
        metadata={
            "name": model.name,
            "version": model.version,
            "replaced_model_id": str(current.id) if current is not None else None,
        },
    )
    db.session.commit()
    return model
