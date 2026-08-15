"""Object-scoped access policy for private transaction evidence."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from momo_fdvs.extensions import db
from momo_fdvs.models import FraudCase, Transaction


def transaction_evidence_access(
    transaction: Transaction,
    *,
    user_id: uuid.UUID,
    roles: set[str],
) -> tuple[bool, bool]:
    """Return visibility and assigned-investigator diagnostic access."""

    if transaction.user_id == user_id:
        return True, False
    if "INVESTIGATOR" not in roles:
        return False, False
    assigned_case_id = db.session.scalar(
        select(FraudCase.id)
        .where(
            FraudCase.transaction_id == transaction.id,
            FraudCase.assigned_to == user_id,
            FraudCase.status.in_(("ASSIGNED", "IN_REVIEW", "REOPENED")),
        )
        .limit(1)
    )
    assigned = assigned_case_id is not None
    return assigned, assigned


__all__ = ["transaction_evidence_access"]
