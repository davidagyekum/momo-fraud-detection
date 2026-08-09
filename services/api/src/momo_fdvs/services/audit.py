"""Append-only safe audit event writer."""

from __future__ import annotations

import uuid
from typing import Any

from flask import g, has_request_context

from momo_fdvs.extensions import db
from momo_fdvs.models import AuditLog


def audit_event(
    action: str,
    outcome: str,
    *,
    actor_id: uuid.UUID | None = None,
    roles: set[str] | None = None,
    target_type: str = "user",
    target_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    request_id = getattr(g, "request_id", None) if has_request_context() else None
    db.session.add(
        AuditLog(
            actor_id=actor_id,
            actor_role_snapshot=sorted(roles or set()),
            action=action,
            target_type=target_type,
            target_id=target_id,
            outcome=outcome,
            request_id=uuid.UUID(request_id) if request_id else uuid.uuid4(),
            metadata_json=metadata or {},
        )
    )
