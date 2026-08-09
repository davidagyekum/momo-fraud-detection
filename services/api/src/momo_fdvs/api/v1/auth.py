"""Authentication and self-profile routes."""

from __future__ import annotations

import hmac
from datetime import UTC, datetime
from typing import Any

from flask import Response, after_this_request, current_app, g, request
from flask.views import MethodView
from flask_smorest import Blueprint
from sqlalchemy import update

from momo_fdvs.api.v1.auth_schemas import (
    AcceptedEnvelopeSchema,
    ChangePasswordSchema,
    ForgotPasswordSchema,
    LoginSchema,
    ProfileUpdateSchema,
    RefreshSchema,
    RegisterSchema,
    ResetPasswordSchema,
    SessionEnvelopeSchema,
    UserEnvelopeSchema,
)
from momo_fdvs.errors import error_response
from momo_fdvs.extensions import db, limiter
from momo_fdvs.models import RefreshSession, User
from momo_fdvs.policies.auth import require_auth, user_roles
from momo_fdvs.security.passwords import hash_password, verify_password
from momo_fdvs.security.tokens import token_hash
from momo_fdvs.services.audit import audit_event
from momo_fdvs.services.auth import (
    AuthFailure,
    SessionTokens,
    authenticate,
    issue_session,
    register_user,
    request_password_reset,
    reset_password,
    revoke_session,
    rotate_session,
    user_projection,
)

auth_blueprint = Blueprint(
    "auth-v1", __name__, url_prefix="/api/v1/auth", description="Authentication and sessions"
)
identity_blueprint = Blueprint(
    "identity-v1", __name__, url_prefix="/api/v1", description="Current user identity"
)


def _meta() -> dict[str, str]:
    return {"request_id": g.request_id}


def _failure(error: AuthFailure) -> Any:
    return error_response(error.code, error.message, error.status)


def _set_cookies(tokens: SessionTokens) -> None:
    @after_this_request
    def apply(response: Response) -> Response:
        common = {
            "secure": current_app.config["AUTH_COOKIE_SECURE"],
            "samesite": current_app.config["AUTH_COOKIE_SAMESITE"],
            "domain": current_app.config["AUTH_COOKIE_DOMAIN"],
            "path": current_app.config["AUTH_COOKIE_PATH"],
        }
        response.set_cookie(
            current_app.config["AUTH_COOKIE_NAME"],
            tokens.refresh_token,
            httponly=True,
            max_age=current_app.config["REFRESH_TOKEN_TTL_DAYS"] * 86400,
            **common,
        )
        response.set_cookie("momo_fdvs_csrf", tokens.csrf_token, httponly=False, **common)
        return response


def _session_payload(user: User, tokens: SessionTokens) -> dict[str, Any]:
    mobile = request.headers.get("X-Client-Type", "").lower() == "mobile"
    if not mobile:
        _set_cookies(tokens)
    return {
        "data": {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token if mobile else None,
            "csrf_token": tokens.csrf_token if mobile else None,
            "expires_in": tokens.expires_in,
            "user": user_projection(user),
        },
        "meta": _meta(),
    }


def _refresh_from_request(data: dict[str, Any]) -> str | None:
    supplied = data.get("refresh_token")
    if supplied:
        return str(supplied)
    cookie = request.cookies.get(current_app.config["AUTH_COOKIE_NAME"])
    csrf_cookie = request.cookies.get("momo_fdvs_csrf", "")
    csrf_header = request.headers.get("X-CSRF-Token", "")
    expected_csrf = token_hash(cookie, current_app.config["CSRF_SECRET"]) if cookie else ""
    if (
        not cookie
        or not csrf_cookie
        or not hmac.compare_digest(csrf_cookie, csrf_header)
        or not hmac.compare_digest(csrf_cookie, expected_csrf)
    ):
        return None
    return cookie


@auth_blueprint.route("/register")
class RegisterResource(MethodView):
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_REGISTRATION"])
    @auth_blueprint.arguments(RegisterSchema)
    @auth_blueprint.response(201, SessionEnvelopeSchema)
    def post(self, data: dict[str, Any]) -> Any:
        try:
            user = register_user(data["full_name"], data["email"], data["password"])
            tokens, _ = issue_session(user)
            return _session_payload(user, tokens)
        except (AuthFailure, ValueError) as exc:
            if isinstance(exc, AuthFailure):
                return _failure(exc)
            return error_response("VALIDATION_ERROR", str(exc), 422)


@auth_blueprint.route("/login")
class LoginResource(MethodView):
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_LOGIN"])
    @auth_blueprint.arguments(LoginSchema)
    @auth_blueprint.response(200, SessionEnvelopeSchema)
    def post(self, data: dict[str, Any]) -> Any:
        try:
            user = authenticate(data["email"], data["password"])
            tokens, _ = issue_session(user)
            return _session_payload(user, tokens)
        except AuthFailure as exc:
            return _failure(exc)


@auth_blueprint.route("/refresh")
class RefreshResource(MethodView):
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_REFRESH"])
    @auth_blueprint.arguments(RefreshSchema)
    @auth_blueprint.response(200, SessionEnvelopeSchema)
    def post(self, data: dict[str, Any]) -> Any:
        raw = _refresh_from_request(data)
        if raw is None:
            return error_response("CSRF_OR_REFRESH_INVALID", "The refresh session is invalid.", 401)
        try:
            user, tokens = rotate_session(raw)
            return _session_payload(user, tokens)
        except AuthFailure as exc:
            return _failure(exc)


@auth_blueprint.route("/logout")
class LogoutResource(MethodView):
    @auth_blueprint.arguments(RefreshSchema)
    @auth_blueprint.response(200, AcceptedEnvelopeSchema)
    def post(self, data: dict[str, Any]) -> Any:
        raw = _refresh_from_request(data)
        if raw:
            revoke_session(raw)

        @after_this_request
        def clear(response: Response) -> Response:
            response.delete_cookie(
                current_app.config["AUTH_COOKIE_NAME"],
                path=current_app.config["AUTH_COOKIE_PATH"],
            )
            response.delete_cookie("momo_fdvs_csrf", path=current_app.config["AUTH_COOKIE_PATH"])
            return response

        return {"data": {"accepted": True}, "meta": _meta()}


@auth_blueprint.route("/forgot-password")
class ForgotPasswordResource(MethodView):
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_PASSWORD_RESET"])
    @auth_blueprint.arguments(ForgotPasswordSchema)
    @auth_blueprint.response(202, AcceptedEnvelopeSchema)
    def post(self, data: dict[str, Any]) -> dict[str, Any]:
        request_password_reset(data["email"])
        return {"data": {"accepted": True}, "meta": _meta()}


@auth_blueprint.route("/reset-password")
class ResetPasswordResource(MethodView):
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_PASSWORD_RESET"])
    @auth_blueprint.arguments(ResetPasswordSchema)
    @auth_blueprint.response(200, AcceptedEnvelopeSchema)
    def post(self, data: dict[str, Any]) -> Any:
        try:
            reset_password(data["token"], data["new_password"])
            return {"data": {"accepted": True}, "meta": _meta()}
        except (AuthFailure, ValueError) as exc:
            if isinstance(exc, AuthFailure):
                return _failure(exc)
            return error_response("VALIDATION_ERROR", str(exc), 422)


@identity_blueprint.route("/me")
class MeResource(MethodView):
    @require_auth
    @identity_blueprint.response(200, UserEnvelopeSchema)
    def get(self) -> dict[str, Any]:
        return {"data": user_projection(g.current_user), "meta": _meta()}

    @require_auth
    @identity_blueprint.arguments(ProfileUpdateSchema)
    @identity_blueprint.response(200, UserEnvelopeSchema)
    def patch(self, data: dict[str, Any]) -> dict[str, Any]:
        if "full_name" in data:
            g.current_user.full_name = data["full_name"].strip()
        if "phone_e164" in data:
            g.current_user.phone_e164 = data["phone_e164"]
        audit_event(
            "profile.updated",
            "SUCCESS",
            actor_id=g.current_user.id,
            roles=set(g.current_roles),
            target_id=g.current_user.id,
        )
        db.session.commit()
        return {"data": user_projection(g.current_user), "meta": _meta()}


@identity_blueprint.route("/me/change-password")
class ChangePasswordResource(MethodView):
    @require_auth
    @identity_blueprint.arguments(ChangePasswordSchema)
    @identity_blueprint.response(200, AcceptedEnvelopeSchema)
    def post(self, data: dict[str, Any]) -> Any:
        if not verify_password(g.current_user.password_hash, data["current_password"]):
            return error_response("INVALID_CREDENTIALS", "Current password is incorrect.", 400)
        try:
            g.current_user.password_hash = hash_password(data["new_password"])
        except ValueError as exc:
            return error_response("VALIDATION_ERROR", str(exc), 422)
        now = datetime.now(UTC)
        g.current_user.password_changed_at = now
        g.current_user.must_change_password = False
        g.current_user.token_version += 1
        db.session.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == g.current_user.id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=now, revoke_reason="PASSWORD_CHANGED")
        )
        audit_event(
            "auth.password_changed",
            "SUCCESS",
            actor_id=g.current_user.id,
            roles=user_roles(g.current_user.id),
            target_id=g.current_user.id,
        )
        db.session.commit()
        return {"data": {"accepted": True}, "meta": _meta()}


__all__ = ["auth_blueprint", "identity_blueprint"]
