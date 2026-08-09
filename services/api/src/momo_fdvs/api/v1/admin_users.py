"""ADMIN-only user and role management routes."""

from __future__ import annotations

import uuid
from typing import Any

from flask import g
from flask.views import MethodView
from flask_smorest import Blueprint

from momo_fdvs.api.v1.admin_user_schemas import (
    AdminRoleUpdateSchema,
    AdminUserCreateSchema,
    AdminUserEnvelopeSchema,
    AdminUserListEnvelopeSchema,
    AdminUserQuerySchema,
    AdminUserUpdateSchema,
)
from momo_fdvs.api.v1.auth_schemas import AcceptedEnvelopeSchema
from momo_fdvs.errors import error_response
from momo_fdvs.policies.auth import require_roles
from momo_fdvs.services.admin_users import (
    admin_projection,
    create_user,
    list_users,
    replace_roles,
    revoke_user_sessions,
    update_user,
)
from momo_fdvs.services.auth import AuthFailure

admin_users_blueprint = Blueprint(
    "admin-users-v1",
    __name__,
    url_prefix="/api/v1/admin/users",
    description="Administrator user management",
)


def _meta() -> dict[str, str]:
    return {"request_id": g.request_id}


def _failure(error: AuthFailure) -> Any:
    return error_response(error.code, error.message, error.status)


@admin_users_blueprint.route("")
class AdminUsersResource(MethodView):
    @require_roles("ADMIN")
    @admin_users_blueprint.arguments(AdminUserQuerySchema, location="query")
    @admin_users_blueprint.response(200, AdminUserListEnvelopeSchema)
    def get(self, query: dict[str, Any]) -> dict[str, Any]:
        users, total = list_users(query)
        return {
            "data": {
                "users": [admin_projection(user) for user in users],
                "page": query["page"],
                "page_size": query["page_size"],
                "total": total,
            },
            "meta": _meta(),
        }

    @require_roles("ADMIN")
    @admin_users_blueprint.arguments(AdminUserCreateSchema)
    @admin_users_blueprint.response(201, AdminUserEnvelopeSchema)
    def post(self, data: dict[str, Any]) -> Any:
        try:
            user = create_user(data, g.current_user, set(g.current_roles))
            return {"data": admin_projection(user), "meta": _meta()}
        except (AuthFailure, ValueError) as exc:
            if isinstance(exc, AuthFailure):
                return _failure(exc)
            return error_response("VALIDATION_ERROR", str(exc), 422)


@admin_users_blueprint.route("/<uuid:user_id>")
class AdminUserResource(MethodView):
    @require_roles("ADMIN")
    @admin_users_blueprint.arguments(AdminUserUpdateSchema)
    @admin_users_blueprint.response(200, AdminUserEnvelopeSchema)
    def patch(self, data: dict[str, Any], user_id: uuid.UUID) -> Any:
        try:
            user = update_user(user_id, data, g.current_user, set(g.current_roles))
            return {"data": admin_projection(user), "meta": _meta()}
        except AuthFailure as exc:
            return _failure(exc)


@admin_users_blueprint.route("/<uuid:user_id>/roles")
class AdminUserRolesResource(MethodView):
    @require_roles("ADMIN")
    @admin_users_blueprint.arguments(AdminRoleUpdateSchema)
    @admin_users_blueprint.response(200, AdminUserEnvelopeSchema)
    def put(self, data: dict[str, Any], user_id: uuid.UUID) -> Any:
        try:
            user = replace_roles(
                user_id,
                set(data["roles"]),
                data["expected_version"],
                g.current_user,
                set(g.current_roles),
            )
            return {"data": admin_projection(user), "meta": _meta()}
        except AuthFailure as exc:
            return _failure(exc)


@admin_users_blueprint.route("/<uuid:user_id>/revoke-sessions")
class AdminUserRevokeSessionsResource(MethodView):
    @require_roles("ADMIN")
    @admin_users_blueprint.response(200, AcceptedEnvelopeSchema)
    def post(self, user_id: uuid.UUID) -> Any:
        try:
            revoke_user_sessions(user_id, g.current_user, set(g.current_roles))
            return {"data": {"accepted": True}, "meta": _meta()}
        except AuthFailure as exc:
            return _failure(exc)


__all__ = ["admin_users_blueprint"]
