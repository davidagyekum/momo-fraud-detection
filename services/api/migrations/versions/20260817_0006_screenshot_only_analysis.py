"""Add immutable screenshot-only analysis evidence links.

Revision ID: 20260817_0006
Revises: 20260816_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260817_0006"
down_revision: str | None = "20260816_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column(
            "analysis_mode",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'combined'"),
        ),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("ocr_result_id", postgresql.UUID(as_uuid=True)),
    )
    op.alter_column(
        "analysis_runs",
        "ocr_confirmation_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_foreign_key(
        op.f("fk_analysis_runs_ocr_result_id_ocr_results"),
        "analysis_runs",
        "ocr_results",
        ["ocr_result_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_analysis_runs_ocr_result_id"),
        "analysis_runs",
        ["ocr_result_id"],
    )
    op.create_check_constraint(
        op.f("ck_analysis_runs_analysis_mode_valid"),
        "analysis_runs",
        "analysis_mode IN ('combined', 'screenshot_only', 'transaction_only')",
    )
    op.create_check_constraint(
        op.f("ck_analysis_runs_evidence_link_valid"),
        "analysis_runs",
        "(analysis_mode = 'screenshot_only' AND ocr_result_id IS NOT NULL "
        "AND ocr_confirmation_id IS NULL) OR "
        "(analysis_mode IN ('combined', 'transaction_only') "
        "AND ocr_confirmation_id IS NOT NULL)",
    )
    op.alter_column("analysis_runs", "analysis_mode", server_default=None)

    op.drop_constraint(
        op.f("ck_verification_results_status_valid"),
        "verification_results",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_verification_results_status_valid"),
        "verification_results",
        "status IN ('VERIFIED', 'UNVERIFIED', 'MISMATCH', 'NOT_ATTEMPTED')",
    )

    # Forward-only repair for the naming-convention duplication introduced by 0004.
    op.execute(
        "ALTER TABLE report_artifacts RENAME CONSTRAINT "
        "ck_report_artifacts_ck_report_artifacts_source_version_positive TO "
        "ck_report_artifacts_source_version_positive"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE report_artifacts RENAME CONSTRAINT "
        "ck_report_artifacts_source_version_positive TO "
        "ck_report_artifacts_ck_report_artifacts_source_version_positive"
    )

    op.drop_constraint(
        op.f("ck_verification_results_status_valid"),
        "verification_results",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_verification_results_status_valid"),
        "verification_results",
        "status IN ('VERIFIED', 'UNVERIFIED', 'MISMATCH')",
    )

    op.drop_constraint(
        op.f("ck_analysis_runs_evidence_link_valid"),
        "analysis_runs",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_analysis_runs_analysis_mode_valid"),
        "analysis_runs",
        type_="check",
    )
    op.drop_index(op.f("ix_analysis_runs_ocr_result_id"), table_name="analysis_runs")
    op.drop_constraint(
        op.f("fk_analysis_runs_ocr_result_id_ocr_results"),
        "analysis_runs",
        type_="foreignkey",
    )
    op.alter_column(
        "analysis_runs",
        "ocr_confirmation_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("analysis_runs", "ocr_result_id")
    op.drop_column("analysis_runs", "analysis_mode")
