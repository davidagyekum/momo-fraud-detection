"""Analytical configuration, execution and immutable result models."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from momo_fdvs.extensions import Base, db
from momo_fdvs.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin


class ModelVersion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        CheckConstraint("model_type IN ('STRUCTURED', 'IMAGE')", name="model_type_valid"),
        CheckConstraint(
            "status IN ('DRAFT', 'READY', 'ACTIVE', 'RETIRED', 'FAILED')",
            name="status_valid",
        ),
        CheckConstraint("char_length(artifact_sha256) = 64", name="artifact_sha256_length"),
        CheckConstraint("char_length(input_schema_hash) = 64", name="schema_hash_length"),
        CheckConstraint(
            "dataset_manifest_hash IS NULL OR char_length(dataset_manifest_hash) = 64",
            name="manifest_hash_length",
        ),
        CheckConstraint(
            "split_hash IS NULL OR char_length(split_hash) = 64", name="split_hash_length"
        ),
        UniqueConstraint("model_type", "name", "version"),
        Index(
            "uq_model_versions_active_type_name",
            "model_type",
            "name",
            unique=True,
            postgresql_where=db.text("status = 'ACTIVE'"),
        ),
    )

    model_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    artifact_uri: Mapped[str] = mapped_column(String(1000), nullable=False)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    input_schema_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    preprocessing_version: Mapped[str] = mapped_column(String(100), nullable=False)
    framework_versions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    dataset_manifest_hash: Mapped[str | None] = mapped_column(String(64))
    split_hash: Mapped[str | None] = mapped_column(String(64))
    training_commit_sha: Mapped[str | None] = mapped_column(String(40))
    model_card_key: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    activated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FraudRuleSet(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "fraud_rule_sets"
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT', 'ACTIVE', 'RETIRED')", name="status_valid"),
        CheckConstraint("row_version >= 1", name="row_version_positive"),
        Index(
            "uq_fraud_rule_sets_active",
            "status",
            unique=True,
            postgresql_where=db.text("status = 'ACTIVE'"),
        ),
    )

    version: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    risk_weights: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    thresholds: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    activated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    rules: Mapped[list[FraudRule]] = relationship(back_populates="rule_set")


class FraudRule(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "fraud_rules"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('INFORMATIONAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="severity_valid",
        ),
        CheckConstraint("score_contribution >= 0", name="score_nonnegative"),
        UniqueConstraint("rule_set_id", "code"),
        Index("ix_fraud_rules_rule_set_id", "rule_set_id"),
    )

    rule_set_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("fraud_rule_sets.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    condition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    score_contribution: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    reason_template: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    rule_set: Mapped[FraudRuleSet] = relationship(back_populates="rules")


class AnalysisRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED', 'PROCESSING', 'COMPLETED', 'PARTIAL', 'FAILED', 'CANCELLED')",
            name="status_valid",
        ),
        CheckConstraint(
            "risk_class IS NULL OR risk_class IN ('GENUINE', 'SUSPICIOUS', 'FRAUDULENT')",
            name="risk_class_valid",
        ),
        CheckConstraint("attempt_count >= 0", name="attempt_count_nonnegative"),
        CheckConstraint(
            "risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 100)",
            name="risk_score_range",
        ),
        CheckConstraint("char_length(request_fingerprint) = 64", name="fingerprint_length"),
        UniqueConstraint("transaction_id", "idempotency_key_hash"),
        Index("ix_analysis_runs_status_queued", "status", "queued_at"),
        Index("ix_analysis_runs_transaction_created", "transaction_id", "created_at"),
        Index("ix_analysis_runs_risk_completed", "risk_class", "completed_at"),
        Index("ix_analysis_runs_current_stage", "current_stage"),
    )

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False
    )
    ocr_confirmation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("ocr_confirmations.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="QUEUED")
    current_stage: Mapped[str | None] = mapped_column(String(50))
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("receipt_templates.id", ondelete="RESTRICT")
    )
    rule_set_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("fraud_rule_sets.id", ondelete="RESTRICT"), nullable=False
    )
    structured_model_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("model_versions.id", ondelete="RESTRICT")
    )
    image_model_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("model_versions.id", ondelete="RESTRICT")
    )
    idempotency_key_hash: Mapped[str | None] = mapped_column(String(64))
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    claimed_by: Mapped[str | None] = mapped_column(String(100))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    risk_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    risk_class: Mapped[str | None] = mapped_column(String(20))
    component_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    top_reasons: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    configuration_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message_safe: Mapped[str | None] = mapped_column(Text)

    transaction: Mapped[Any] = relationship(
        "Transaction", foreign_keys=[transaction_id], back_populates="analysis_runs"
    )
    stages: Mapped[list[AnalysisStageRun]] = relationship(back_populates="analysis_run")


class AnalysisStageRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "analysis_stage_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'SKIPPED', 'FAILED')",
            name="status_valid",
        ),
        CheckConstraint("attempt >= 1", name="attempt_positive"),
        CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="duration_nonnegative"),
        UniqueConstraint("analysis_run_id", "stage", "attempt"),
        Index("ix_analysis_stage_runs_analysis_run_id", "analysis_run_id"),
    )

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("analysis_runs.id", ondelete="RESTRICT"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="QUEUED")
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(100))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="stages")


class ImageAnalysis(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "image_analyses"
    __table_args__ = (
        CheckConstraint(
            "image_tamper_probability IS NULL OR "
            "(image_tamper_probability >= 0 AND image_tamper_probability <= 1)",
            name="tamper_probability_range",
        ),
    )

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("analysis_runs.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    algorithm_version: Mapped[str] = mapped_column(String(100), nullable=False)
    metadata_evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    duplicate_evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    compression_evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    noise_evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    layout_evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    quality_evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    engineered_features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    image_tamper_probability: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    warnings: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)


class FraudPrediction(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "fraud_predictions"
    __table_args__ = (
        CheckConstraint("prediction_type IN ('STRUCTURED', 'IMAGE')", name="type_valid"),
        CheckConstraint(
            "predicted_class IS NULL OR predicted_class IN ('GENUINE', 'SUSPICIOUS', 'FRAUDULENT')",
            name="class_valid",
        ),
        CheckConstraint("status IN ('SUCCESS', 'UNAVAILABLE', 'ERROR')", name="status_valid"),
        CheckConstraint("char_length(feature_schema_hash) = 64", name="schema_hash_length"),
        CheckConstraint("inference_ms IS NULL OR inference_ms >= 0", name="inference_nonnegative"),
        UniqueConstraint("analysis_run_id", "prediction_type"),
        Index("ix_fraud_predictions_analysis_run_id", "analysis_run_id"),
    )

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("analysis_runs.id", ondelete="RESTRICT"), nullable=False
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False
    )
    prediction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    predicted_class: Mapped[str | None] = mapped_column(String(20))
    probabilities: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    feature_schema_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    inference_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100))


class RuleEvaluation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "rule_evaluations"
    __table_args__ = (
        CheckConstraint("score_contribution >= 0", name="score_nonnegative"),
        UniqueConstraint("analysis_run_id", "rule_id"),
        Index("ix_rule_evaluations_analysis_run_id", "analysis_run_id"),
    )

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("analysis_runs.id", ondelete="RESTRICT"), nullable=False
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("fraud_rules.id", ondelete="RESTRICT"), nullable=False
    )
    triggered: Mapped[bool] = mapped_column(Boolean, nullable=False)
    observed_value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    score_contribution: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    reason_text: Mapped[str] = mapped_column(Text, nullable=False)
