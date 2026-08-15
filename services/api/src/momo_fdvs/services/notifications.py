"""Owner-scoped in-app notification creation primitives."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

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
    try:
        with db.session.begin_nested():
            db.session.add(notification)
            db.session.flush()
        return notification
    except IntegrityError:
        existing = db.session.scalar(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.dedupe_key == dedupe_key,
            )
        )
        if existing is None:
            raise
        return existing


def notify_analysis_outcome(
    *,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
    analysis_run_id: uuid.UUID,
    analysis_status: str,
    risk_band: str,
) -> list[Notification]:
    """Persist safe, deduplicated outcome notifications before domain commit."""

    notifications = [
        create_notification(
            user_id=user_id,
            notification_type="ANALYSIS_COMPLETED",
            title="Analysis ready",
            message=f"Your transaction analysis completed with status {analysis_status.lower()}.",
            dedupe_key=f"analysis-completed:{analysis_run_id}",
            target_type="ANALYSIS",
            target_id=analysis_run_id,
        )
    ]
    if risk_band.lower() == "high":
        notifications.append(
            create_notification(
                user_id=user_id,
                notification_type="HIGH_RISK_DETECTED",
                title="High-risk result",
                message="A transaction analysis needs your attention.",
                dedupe_key=f"analysis-high-risk:{analysis_run_id}",
                target_type="TRANSACTION",
                target_id=transaction_id,
            )
        )
    return notifications


def notification_projection(notification: Notification) -> dict[str, Any]:
    target = None
    if notification.target_type is not None and notification.target_id is not None:
        target = {"type": notification.target_type, "id": notification.target_id}
    return {
        "id": notification.id,
        "type": notification.type,
        "title": notification.title,
        "message": notification.message,
        "target": target,
        "read_at": notification.read_at,
        "created_at": notification.created_at,
    }


def list_notifications(
    *, user_id: uuid.UUID, unread_only: bool, page: int, page_size: int
) -> tuple[list[Notification], int]:
    predicate = [Notification.user_id == user_id]
    if unread_only:
        predicate.append(Notification.read_at.is_(None))
    total = db.session.scalar(select(func.count()).select_from(Notification).where(*predicate)) or 0
    items = list(
        db.session.scalars(
            select(Notification)
            .where(*predicate)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return items, total


def unread_notification_count(user_id: uuid.UUID) -> int:
    return int(
        db.session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        )
        or 0
    )


def mark_notification_read(user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification | None:
    notification = db.session.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    if notification is None:
        return None
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
    return notification


def mark_all_notifications_read(user_id: uuid.UUID) -> int:
    unread = unread_notification_count(user_id)
    db.session.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(UTC))
    )
    return unread


__all__ = [
    "create_notification",
    "list_notifications",
    "mark_all_notifications_read",
    "mark_notification_read",
    "notification_projection",
    "notify_analysis_outcome",
    "unread_notification_count",
]
