"""Protect terminal analysis and stage evidence from mutation.

Revision ID: 20260815_0003
Revises: 20260809_0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260815_0003"
down_revision: str | None = "20260809_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TRIGGER trg_analysis_stage_runs_immutable "
        "BEFORE UPDATE OR DELETE ON analysis_stage_runs FOR EACH ROW "
        "EXECUTE FUNCTION prevent_immutable_evidence_mutation()"
    )
    op.execute(
        """
        CREATE FUNCTION prevent_terminal_analysis_mutation() RETURNS trigger AS $$
        BEGIN
            IF OLD.status IN ('COMPLETED', 'PARTIAL', 'FAILED', 'CANCELLED') THEN
                RAISE EXCEPTION 'terminal analysis evidence cannot be modified'
                    USING ERRCODE = '55000';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER trg_analysis_runs_terminal_immutable "
        "BEFORE UPDATE OR DELETE ON analysis_runs FOR EACH ROW "
        "EXECUTE FUNCTION prevent_terminal_analysis_mutation()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_analysis_runs_terminal_immutable ON analysis_runs")
    op.execute("DROP FUNCTION prevent_terminal_analysis_mutation()")
    op.execute("DROP TRIGGER trg_analysis_stage_runs_immutable ON analysis_stage_runs")
