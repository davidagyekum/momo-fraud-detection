"""Authentication and session lifecycle service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from flask import current_app
from sqlalchemy import select, update

from momo_fdvs.extensions import db
from momo_fdvs.models import PasswordResetToken, RefreshSession, Role, User, UserRole
from momo_fdvs.policies.auth import user_roles
from momo_fdvs.security.passwords import TIMING_HASH, hash_password, needs_rehash, verify_password
from momo_fdvs.security.tokens import encode_access_token, opaque_token, token_hash
from momo_fdvs.services.audit import audit_event


class AuthFailure(ValueError):
    def __init__(self, code: str, message: str, status: int = 401) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


@dataclass(frozen=True)
class SessionTokens:
    access_token: str
    refresh_token: str
    csrf_token: str
    expires_in: int


def user_projection(user: User) -> dict[str, object]:
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "email": str(user.email),
        "phone_e164": user.phone_e164,
        "roles": sorted(user_roles(user.id)),
        "status": user.status,
        "must_change_password": user.must_change_password,
    }


def register_user(full_name: str, email: str, password: str) -> User:
    if not current_app.config["SELF_REGISTRATION_ENABLED"]:
        raise AuthFailure("REGISTRATION_DISABLED", "Registration is unavailable.", 403)
    normalized = email.strip().lower()
    if db.session.scalar(select(User.id).where(User.email == normalized)) is not None:
        raise AuthFailure("ACCOUNT_EXISTS", "An account with that email already exists.", 409)
    if db.session.get(Role, "USER") is None:
        raise AuthFailure("DEPENDENCY_UNAVAILABLE", "Registration is temporarily unavailable.", 503)
    user = User(
        email=normalized,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        status="ACTIVE",
        password_changed_at=datetime.now(UTC),
        must_change_password=False,
    )
    db.session.add(user)
    db.session.flush()
    db.session.add(
        UserRole(user_id=user.id, role_code="USER", granted_by=None, granted_at=datetime.now(UTC))
    )
    audit_event("auth.register", "SUCCESS", actor_id=user.id, roles={"USER"}, target_id=user.id)
    db.session.commit()
    return user


def authenticate(email: str, password: str) -> User:
    user = db.session.scalar(select(User).where(User.email == email.strip().lower()))
    encoded = user.password_hash if user is not None else TIMING_HASH
    password_valid = verify_password(encoded, password)
    if user is None or not password_valid or user.status != "ACTIVE":
        audit_event("auth.login", "FAILURE", metadata={"reason": "invalid_credentials"})
        db.session.commit()
        raise AuthFailure("INVALID_CREDENTIALS", "Email or password is incorrect.")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = datetime.now(UTC)
    audit_event(
        "auth.login", "SUCCESS", actor_id=user.id, roles=user_roles(user.id), target_id=user.id
    )
    db.session.commit()
    return user


def issue_session(
    user: User, family_id: uuid.UUID | None = None, *, commit: bool = True
) -> tuple[SessionTokens, RefreshSession]:
    roles = user_roles(user.id)
    refresh = opaque_token()
    csrf = token_hash(refresh, current_app.config["CSRF_SECRET"])
    now = datetime.now(UTC)
    session = RefreshSession(
        user_id=user.id,
        family_id=family_id or uuid.uuid4(),
        token_hash=token_hash(refresh, current_app.config["JWT_REFRESH_SECRET"]),
        expires_at=now + timedelta(days=current_app.config["REFRESH_TOKEN_TTL_DAYS"]),
    )
    db.session.add(session)
    db.session.flush()
    if commit:
        db.session.commit()
    ttl = current_app.config["ACCESS_TOKEN_TTL_MINUTES"]
    return (
        SessionTokens(
            encode_access_token(
                user_id=user.id,
                roles=roles,
                token_version=user.token_version,
                secret=current_app.config["JWT_ACCESS_SECRET"],
                ttl_minutes=ttl,
            ),
            refresh,
            csrf,
            ttl * 60,
        ),
        session,
    )


def rotate_session(raw_token: str) -> tuple[User, SessionTokens]:
    digest = token_hash(raw_token, current_app.config["JWT_REFRESH_SECRET"])
    session = db.session.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == digest).with_for_update()
    )
    now = datetime.now(UTC)
    if session is None:
        raise AuthFailure("INVALID_REFRESH", "The refresh session is invalid.")
    if session.revoked_at is not None:
        db.session.execute(
            update(RefreshSession)
            .where(
                RefreshSession.family_id == session.family_id, RefreshSession.revoked_at.is_(None)
            )
            .values(revoked_at=now, revoke_reason="REUSE_DETECTED")
        )
        audit_event(
            "auth.refresh_reuse", "FAILURE", actor_id=session.user_id, target_id=session.user_id
        )
        db.session.commit()
        raise AuthFailure("REFRESH_REUSE_DETECTED", "The refresh session is invalid.")
    user = db.session.get(User, session.user_id)
    if user is None or user.status != "ACTIVE" or session.expires_at <= now:
        raise AuthFailure("INVALID_REFRESH", "The refresh session is invalid.")
    tokens, replacement = issue_session(user, family_id=session.family_id, commit=False)
    session.revoked_at = now
    session.revoke_reason = "ROTATED"
    session.replaced_by_id = replacement.id
    audit_event("auth.refresh_rotated", "SUCCESS", actor_id=user.id, target_id=user.id)
    db.session.commit()
    return user, tokens


def revoke_session(raw_token: str, reason: str = "LOGOUT") -> None:
    digest = token_hash(raw_token, current_app.config["JWT_REFRESH_SECRET"])
    session = db.session.scalar(select(RefreshSession).where(RefreshSession.token_hash == digest))
    if session and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        session.revoke_reason = reason
        audit_event(
            "auth.session_revoked", "SUCCESS", actor_id=session.user_id, target_id=session.user_id
        )
        db.session.commit()


def request_password_reset(email: str) -> None:
    user = db.session.scalar(select(User).where(User.email == email.strip().lower()))
    raw = opaque_token()
    digest = token_hash(raw, current_app.config["JWT_REFRESH_SECRET"])
    accepted_user = user if user is not None and user.status == "ACTIVE" else None
    if accepted_user is not None:
        db.session.add(
            PasswordResetToken(
                user_id=accepted_user.id,
                token_hash=digest,
                expires_at=datetime.now(UTC)
                + timedelta(minutes=current_app.config["PASSWORD_RESET_TTL_MINUTES"]),
            )
        )
    audit_event(
        "auth.password_reset_requested",
        "SUCCESS",
        actor_id=accepted_user.id if accepted_user is not None else None,
        target_id=accepted_user.id if accepted_user is not None else None,
    )
    db.session.commit()
    if current_app.testing and accepted_user is not None:
        current_app.extensions.setdefault("password_reset_outbox", []).append(
            {"user_id": str(accepted_user.id), "token": raw}
        )


def reset_password(raw_token: str, new_password: str) -> User:
    digest = token_hash(raw_token, current_app.config["JWT_REFRESH_SECRET"])
    reset = db.session.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == digest)
    )
    now = datetime.now(UTC)
    if reset is None or reset.used_at is not None or reset.expires_at <= now:
        raise AuthFailure("INVALID_RESET_TOKEN", "The reset token is invalid or expired.", 400)
    user = db.session.get(User, reset.user_id)
    if user is None:
        raise AuthFailure("INVALID_RESET_TOKEN", "The reset token is invalid or expired.", 400)
    user.password_hash = hash_password(new_password)
    user.password_changed_at = now
    user.must_change_password = False
    user.token_version += 1
    reset.used_at = now
    db.session.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=now, revoke_reason="PASSWORD_RESET")
    )
    audit_event("auth.password_reset", "SUCCESS", actor_id=user.id, target_id=user.id)
    db.session.commit()
    return user
