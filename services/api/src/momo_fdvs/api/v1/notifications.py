"""Authenticated owner notification inbox."""

from __future__ import annotations

import math
import uuid
from typing import Any

from flask import g
from flask.views import MethodView
from flask_smorest import Blueprint

from momo_fdvs.api.v1.notification_schemas import (
    NotificationEnvelopeSchema,
    NotificationListEnvelopeSchema,
    NotificationQuerySchema,
    ReadAllEnvelopeSchema,
    UnreadCountEnvelopeSchema,
)
from momo_fdvs.errors import error_response
from momo_fdvs.extensions import db
from momo_fdvs.policies.auth import require_auth
from momo_fdvs.services.audit import audit_event
from momo_fdvs.services.notifications import (
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    notification_projection,
    unread_notification_count,
)

notifications_blueprint = Blueprint(
    "notifications-v1",
    __name__,
    url_prefix="/api/v1/notifications",
    description="Owner-scoped in-app notifications",
)


def _meta() -> dict[str, str]:
    return {"request_id": g.request_id}


@notifications_blueprint.route("")
class NotificationListResource(MethodView):
    @require_auth
    @notifications_blueprint.arguments(NotificationQuerySchema, location="query")
    @notifications_blueprint.response(200, NotificationListEnvelopeSchema)
    def get(self, query: dict[str, Any]) -> dict[str, Any]:
        """List only the authenticated user's notifications."""
        page = int(query["page"])
        page_size = int(query["page_size"])
        items, total = list_notifications(
            user_id=g.current_user.id,
            unread_only=bool(query["unread"]),
            page=page,
            page_size=page_size,
        )
        return {
            "data": {
                "items": [notification_projection(item) for item in items],
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": math.ceil(total / page_size),
            },
            "meta": _meta(),
        }


@notifications_blueprint.route("/unread-count")
class NotificationUnreadCountResource(MethodView):
    @require_auth
    @notifications_blueprint.response(200, UnreadCountEnvelopeSchema)
    def get(self) -> dict[str, Any]:
        """Return the authenticated user's unread count."""
        return {
            "data": {"unread_count": unread_notification_count(g.current_user.id)},
            "meta": _meta(),
        }


@notifications_blueprint.route("/<uuid:notification_id>/read")
class NotificationReadResource(MethodView):
    @require_auth
    @notifications_blueprint.response(200, NotificationEnvelopeSchema)
    def post(self, notification_id: uuid.UUID) -> Any:
        """Idempotently mark one owned notification as read."""
        notification = mark_notification_read(g.current_user.id, notification_id)
        if notification is None:
            return error_response("NOTIFICATION_NOT_FOUND", "Notification not found.", 404)
        audit_event(
            "notification.read",
            "SUCCESS",
            actor_id=g.current_user.id,
            roles=set(g.current_roles),
            target_type="notification",
            target_id=notification.id,
        )
        db.session.commit()
        return {"data": notification_projection(notification), "meta": _meta()}


@notifications_blueprint.route("/read-all")
class NotificationReadAllResource(MethodView):
    @require_auth
    @notifications_blueprint.response(200, ReadAllEnvelopeSchema)
    def post(self) -> dict[str, Any]:
        """Idempotently mark all of the authenticated user's notifications read."""
        marked_read = mark_all_notifications_read(g.current_user.id)
        audit_event(
            "notification.read_all",
            "SUCCESS",
            actor_id=g.current_user.id,
            roles=set(g.current_roles),
            target_type="notification",
            metadata={"marked_read": marked_read},
        )
        db.session.commit()
        return {
            "data": {"marked_read": marked_read, "unread_count": 0},
            "meta": _meta(),
        }


__all__ = ["notifications_blueprint"]
