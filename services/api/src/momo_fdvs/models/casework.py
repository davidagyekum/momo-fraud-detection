"""Fraud cases, reporting, notifications, audit and idempotency models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from momo_fdvs.extensions import Base, db
from momo_fdvs.models.base import CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class FraudCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fraud_cases"
    __table_args__ = (
        CheckConstraint(
            "source IN ('USER_REPORT', 'AUTO_HIGH_RISK', 'ADMIN')", name="source_valid"
        ),
        CheckConstraint(
            "status IN ('OPEN', 'ASSIGNED', 'IN_REVIEW', 'DECIDED', 'CLOSED', 'REOPENED')",
            name="status_valid",
        ),
        Index("ix_fraud_cases_transaction_id", "transaction_id"),
        Index("ix_fraud_cases_status_assigned_opened", "status", "assigned_to", "opened_at"),
        Index(
            "uq_fraud_cases_active_transaction_source",
            "transaction_id",
            "source",
            unique=True,
            postgresql_where=db.text("status IN ('OPEN', 'ASSIGNED', 'IN_REVIEW', 'REOPENED')"),
        ),
    )

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    reporter_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    events: Mapped[list[CaseEvent]] = relationship(back_populates="case")
    decisions: Mapped[list[CaseDecision]] = relationship(back_populates="case")


class CaseEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "case_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('OPENED', 'ASSIGNED', 'NOTE', 'STATUS', 'DECISION', 'REOPENED')",
            name="event_type_valid",
        ),
        CheckConstraint(
            "event_type <> 'DECISION' OR (reason IS NOT NULL AND char_length(trim(reason)) > 0)",
            name="decision_reason_required",
        ),
        Index("ix_case_events_case_id", "case_id"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("fraud_cases.id", ondelete="RESTRICT"), nullable=False
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str | None] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    case: Mapped[FraudCase] = relationship(back_populates="events")


class CaseDecision(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "case_decisions"
    __table_args__ = (
        CheckConstraint("outcome IN ('CONFIRMED', 'DISMISSED', 'ESCALATED')", name="outcome_valid"),
        CheckConstraint("char_length(trim(reason)) > 0", name="reason_required"),
        Index("ix_case_decisions_case_id", "case_id"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("fraud_cases.id", ondelete="RESTRICT"), nullable=False
    )
    decided_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("case_decisions.id", ondelete="RESTRICT")
    )

    case: Mapped[FraudCase] = relationship(back_populates="decisions")
    supersedes: Mapped[CaseDecision | None] = relationship(remote_side="CaseDecision.id")


class ReportArtifact(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "report_artifacts"
    __table_args__ = (
        CheckConstraint(
            "report_type IN ('ANALYSIS', 'CASE', 'OPERATIONS')", name="report_type_valid"
        ),
        CheckConstraint(
            "status IN ('GENERATING', 'READY', 'FAILED', 'EXPIRED')", name="status_valid"
        ),
        CheckConstraint("char_length(sha256) = 64", name="sha256_length"),
        CheckConstraint(
            "(report_type = 'ANALYSIS' AND transaction_id IS NOT NULL AND case_id IS NULL) OR "
            "(report_type = 'CASE' AND case_id IS NOT NULL) OR "
            "(report_type = 'OPERATIONS' AND transaction_id IS NULL AND case_id IS NULL)",
            name="target_valid",
        ),
    )

    report_type: Mapped[str] = mapped_column(String(30), nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT")
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("fraud_cases.id", ondelete="RESTRICT")
    )
    object_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="GENERATING")
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Notification(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "(target_type IS NULL AND target_id IS NULL) OR "
            "(target_type IS NOT NULL AND target_id IS NOT NULL)",
            name="target_pair_valid",
        ),
        Index("ix_notifications_user_read_created", "user_id", "read_at", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(50))
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_status: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class AuditLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint("outcome IN ('SUCCESS', 'FAILURE', 'DENIED')", name="outcome_valid"),
        CheckConstraint("ip_hash IS NULL OR char_length(ip_hash) = 64", name="ip_hash_length"),
        CheckConstraint(
            "user_agent_hash IS NULL OR char_length(user_agent_hash) = 64",
            name="user_agent_hash_length",
        ),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_actor_created", "actor_id", "created_at"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
        Index("ix_audit_logs_target", "target_type", "target_id"),
        Index("ix_audit_logs_request_id", "request_id"),
    )

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    actor_role_snapshot: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    user_agent_hash: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )


class IdempotencyRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        CheckConstraint("char_length(key_hash) = 64", name="key_hash_length"),
        CheckConstraint("char_length(request_hash) = 64", name="request_hash_length"),
        UniqueConstraint("principal_id", "scope", "key_hash"),
        Index("ix_idempotency_records_expires_at", "expires_at"),
    )

    principal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(50))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    response_status: Mapped[int | None] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
