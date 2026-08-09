"""Imported reference transaction and verification-result models."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from momo_fdvs.extensions import Base, db
from momo_fdvs.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin


class ReferenceImportBatch(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "reference_import_batches"
    __table_args__ = (
        CheckConstraint(
            "status IN ('UPLOADED', 'VALIDATED', 'COMMITTED', 'FAILED')", name="status_valid"
        ),
        CheckConstraint("total_rows >= 0", name="total_rows_nonnegative"),
        CheckConstraint("valid_rows >= 0", name="valid_rows_nonnegative"),
        CheckConstraint("invalid_rows >= 0", name="invalid_rows_nonnegative"),
        CheckConstraint("char_length(file_sha256) = 64", name="file_hash_length"),
        UniqueConstraint("source_label", "file_sha256"),
        Index("ix_reference_import_batches_file_sha256", "file_sha256"),
    )

    source_label: Mapped[str] = mapped_column(String(200), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    object_key: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="UPLOADED")
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_report_key: Mapped[str | None] = mapped_column(String(500))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    transactions: Mapped[list[ReferenceTransaction]] = relationship(back_populates="import_batch")


class ReferenceTransaction(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "reference_transactions"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_nonnegative"),
        CheckConstraint("char_length(currency) = 3", name="currency_length"),
        UniqueConstraint(
            "provider_code",
            "transaction_reference",
            "import_batch_id",
            name="uq_reference_transactions_batch_reference",
        ),
        Index(
            "uq_reference_transactions_source_id",
            "provider_code",
            "transaction_reference",
            "source_system_id",
            unique=True,
            postgresql_where=db.text("source_system_id IS NOT NULL"),
        ),
        Index(
            "ix_reference_transactions_provider_reference",
            "provider_code",
            "transaction_reference",
        ),
        Index("ix_reference_transactions_occurred_at", "occurred_at"),
    )

    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("reference_import_batches.id", ondelete="RESTRICT"), nullable=False
    )
    provider_code: Mapped[str] = mapped_column(String(50), nullable=False)
    transaction_reference: Mapped[str] = mapped_column(String(150), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GHS")
    sender_name_normalised: Mapped[str | None] = mapped_column(String(200))
    sender_phone_e164: Mapped[str | None] = mapped_column(String(20))
    receiver_name_normalised: Mapped[str | None] = mapped_column(String(200))
    receiver_phone_e164: Mapped[str | None] = mapped_column(String(20))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transaction_status: Mapped[str | None] = mapped_column(String(50))
    source_system_id: Mapped[str | None] = mapped_column(String(150))
    raw_row: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    import_batch: Mapped[ReferenceImportBatch] = relationship(back_populates="transactions")


class VerificationResult(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "verification_results"
    __table_args__ = (
        CheckConstraint("status IN ('VERIFIED', 'UNVERIFIED', 'MISMATCH')", name="status_valid"),
        CheckConstraint("matched_field_count >= 0", name="matched_nonnegative"),
        CheckConstraint("mismatched_field_count >= 0", name="mismatched_nonnegative"),
        Index("ix_verification_results_status_created", "status", "created_at"),
    )

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("analysis_runs.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    reference_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("reference_transactions.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    verifier_version: Mapped[str] = mapped_column(String(100), nullable=False)
    candidate_method: Mapped[str] = mapped_column(String(100), nullable=False)
    field_comparisons: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    matched_field_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mismatched_field_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
