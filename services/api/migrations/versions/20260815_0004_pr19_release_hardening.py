"""Add PR19 case concurrency, notification and report identities.

Revision ID: 20260815_0004
Revises: 20260815_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260815_0004"
down_revision: str | None = "20260815_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "fraud_cases",
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.drop_index(
        "uq_fraud_cases_active_transaction_source",
        table_name="fraud_cases",
        postgresql_where=sa.text("status IN ('OPEN', 'ASSIGNED', 'IN_REVIEW', 'REOPENED')"),
    )
    op.create_index(
        "uq_fraud_cases_active_transaction",
        "fraud_cases",
        ["transaction_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('OPEN', 'ASSIGNED', 'IN_REVIEW', 'REOPENED')"),
    )

    op.add_column("notifications", sa.Column("dedupe_key", sa.String(length=200)))
    op.create_unique_constraint(
        "uq_notifications_user_id_dedupe_key", "notifications", ["user_id", "dedupe_key"]
    )

    op.add_column(
        "report_artifacts",
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True)),
    )
    op.add_column("report_artifacts", sa.Column("source_version", sa.Integer()))
    op.create_foreign_key(
        "fk_report_artifacts_analysis_run_id_analysis_runs",
        "report_artifacts",
        "analysis_runs",
        ["analysis_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_report_artifacts_source_version_positive",
        "report_artifacts",
        "source_version IS NULL OR source_version >= 1",
    )
    op.create_index("ix_report_artifacts_analysis_run_id", "report_artifacts", ["analysis_run_id"])


def downgrade() -> None:
    op.drop_index("ix_report_artifacts_analysis_run_id", table_name="report_artifacts")
    op.drop_constraint(
        "ck_report_artifacts_source_version_positive", "report_artifacts", type_="check"
    )
    op.drop_constraint(
        "fk_report_artifacts_analysis_run_id_analysis_runs",
        "report_artifacts",
        type_="foreignkey",
    )
    op.drop_column("report_artifacts", "source_version")
    op.drop_column("report_artifacts", "analysis_run_id")

    op.drop_constraint("uq_notifications_user_id_dedupe_key", "notifications", type_="unique")
    op.drop_column("notifications", "dedupe_key")

    op.drop_index(
        "uq_fraud_cases_active_transaction",
        table_name="fraud_cases",
        postgresql_where=sa.text("status IN ('OPEN', 'ASSIGNED', 'IN_REVIEW', 'REOPENED')"),
    )
    op.create_index(
        "uq_fraud_cases_active_transaction_source",
        "fraud_cases",
        ["transaction_id", "source"],
        unique=True,
        postgresql_where=sa.text("status IN ('OPEN', 'ASSIGNED', 'IN_REVIEW', 'REOPENED')"),
    )
    op.drop_column("fraud_cases", "version")
