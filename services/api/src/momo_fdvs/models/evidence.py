"""Receipt submission and OCR evidence models."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
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
from momo_fdvs.models.base import CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from momo_fdvs.models.analysis import AnalysisRun
    from momo_fdvs.models.identity import User


class Transaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'UPLOADED', 'OCR_PENDING', 'OCR_REVIEW', 'READY', "
            "'ANALYSIS_QUEUED', 'ANALYSING', 'COMPLETED', 'PARTIAL', 'FAILED', 'DELETED')",
            name="status_valid",
        ),
        Index("ix_transactions_user_created", "user_id", "created_at"),
        Index("ix_transactions_status_created", "status", "created_at"),
        Index("ix_transactions_provider_code", "provider_code"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    provider_code: Mapped[str | None] = mapped_column(String(50))
    display_reference_masked: Mapped[str | None] = mapped_column(String(100))
    latest_analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "analysis_runs.id",
            name="fk_transactions_latest_analysis_run_id_analysis_runs",
            use_alter=True,
            ondelete="RESTRICT",
        ),
    )

    user: Mapped[User] = relationship(back_populates="transactions")
    receipt: Mapped[Receipt | None] = relationship(back_populates="transaction", uselist=False)
    analysis_runs: Mapped[list[AnalysisRun]] = relationship(
        foreign_keys="AnalysisRun.transaction_id", back_populates="transaction"
    )
    latest_analysis_run: Mapped[AnalysisRun | None] = relationship(
        foreign_keys=[latest_analysis_run_id], post_update=True
    )


class Receipt(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "receipts"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="size_positive"),
        CheckConstraint("width_px > 0", name="width_positive"),
        CheckConstraint("height_px > 0", name="height_positive"),
        CheckConstraint("char_length(sha256) = 64", name="sha256_length"),
        CheckConstraint(
            "quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 1)",
            name="quality_score_range",
        ),
        Index("ix_receipts_sha256", "sha256"),
        Index("ix_receipts_perceptual_hash", "perceptual_hash"),
    )

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    object_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(50), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width_px: Mapped[int] = mapped_column(Integer, nullable=False)
    height_px: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    perceptual_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    quality_warnings: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    storage_version: Mapped[str] = mapped_column(String(30), nullable=False)

    transaction: Mapped[Transaction] = relationship(back_populates="receipt")
    derivatives: Mapped[list[ReceiptDerivative]] = relationship(back_populates="receipt")
    ocr_results: Mapped[list[OCRResult]] = relationship(back_populates="receipt")


class ReceiptDerivative(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "receipt_derivatives"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('THUMBNAIL', 'OCR_VARIANT', 'ELA', 'NOISE_MAP', 'HEATMAP')",
            name="kind_valid",
        ),
        CheckConstraint("char_length(sha256) = 64", name="sha256_length"),
        UniqueConstraint("receipt_id", "kind", "version", "sha256"),
        Index("ix_receipt_derivatives_receipt_id", "receipt_id"),
    )

    receipt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("receipts.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    receipt: Mapped[Receipt] = relationship(back_populates="derivatives")


class ReceiptTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "receipt_templates"
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT', 'ACTIVE', 'RETIRED')", name="status_valid"),
        CheckConstraint("row_version >= 1", name="row_version_positive"),
        UniqueConstraint("provider_code", "version"),
        Index(
            "uq_receipt_templates_active_provider",
            "provider_code",
            unique=True,
            postgresql_where=db.text("status = 'ACTIVE'"),
        ),
    )

    provider_code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    parser_version: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    activated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class OCRResult(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "ocr_results"
    __table_args__ = (
        CheckConstraint(
            "required_field_accuracy_hint IS NULL OR "
            "(required_field_accuracy_hint >= 0 AND required_field_accuracy_hint <= 1)",
            name="accuracy_hint_range",
        ),
        Index("ix_ocr_results_receipt_created", "receipt_id", "created_at"),
    )

    receipt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("receipts.id", ondelete="RESTRICT"), nullable=False
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("receipt_templates.id", ondelete="RESTRICT")
    )
    engine_name: Mapped[str] = mapped_column(String(50), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(100), nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(100), nullable=False)
    selected_variant: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    token_data: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    extracted_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    field_confidences: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    warnings: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    required_field_accuracy_hint: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))

    receipt: Mapped[Receipt] = relationship(back_populates="ocr_results")
    template: Mapped[ReceiptTemplate | None] = relationship()
    confirmations: Mapped[list[OCRConfirmation]] = relationship(back_populates="ocr_result")


class OCRConfirmation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ocr_confirmations"
    __table_args__ = (
        Index("ix_ocr_confirmations_ocr_result_id", "ocr_result_id"),
        Index("ix_ocr_confirmations_transaction_confirmed", "transaction_id", "confirmed_at"),
    )

    ocr_result_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("ocr_results.id", ondelete="RESTRICT"), nullable=False
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False
    )
    confirmed_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    corrections: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    confirmed_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False)

    ocr_result: Mapped[OCRResult] = relationship(back_populates="confirmations")
    transaction: Mapped[Transaction] = relationship()
