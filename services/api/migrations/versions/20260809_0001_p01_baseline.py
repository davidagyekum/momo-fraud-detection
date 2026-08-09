"""Establish the empty P01 migration baseline.

Revision ID: 20260809_0001
Revises: None
"""

from collections.abc import Sequence

revision: str = "20260809_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Reserve an auditable baseline before P02 creates domain tables."""


def downgrade() -> None:
    """The empty baseline has no objects to remove."""
