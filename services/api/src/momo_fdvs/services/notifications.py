"""Owner-scoped in-app notification creation primitives."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from momo_fdvs.extensions import db
from momo_fdvs.models import Notification


def create_notification(
    *,
    user_id: uuid.UUID,
    notification_type: str,
    title: str,
    message: str,
    dedupe_key: str,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
) -> Notification:
    """Create at most one in-app notification for a safe domain event."""

    existing = db.session.scalar(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.dedupe_key == dedupe_key,
        )
    )
    if existing is not None:
        return existing
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        dedupe_key=dedupe_key,
        target_type=target_type,
        target_id=target_id,
        delivery_status={"in_app": "DELIVERED", "external": "DISABLED"},
    )
    db.session.add(notification)
    return notification


__all__ = ["create_notification"]
