"""Seed required identity role reference data.

Revision ID: 20260816_0005
Revises: 20260815_0004
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260816_0005"
down_revision: str | None = "20260815_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO roles (code, description)
        VALUES
            ('USER', 'Receipt-submitting merchant or end user'),
            ('ADMIN', 'System and governance administrator'),
            ('INVESTIGATOR', 'Fraud investigation officer')
        ON CONFLICT (code) DO UPDATE
        SET description = EXCLUDED.description
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM roles AS role
        WHERE role.code IN ('USER', 'ADMIN', 'INVESTIGATOR')
          AND NOT EXISTS (
              SELECT 1 FROM user_roles AS grant_row
              WHERE grant_row.role_code = role.code
          )
        """
    )
