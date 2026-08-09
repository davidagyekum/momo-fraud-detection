"""Administrator user-management operations and policy safeguards."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select, update

from momo_fdvs.extensions import db
from momo_fdvs.models import RefreshSession, Role, User, UserRole
from momo_fdvs.policies.auth import user_roles
from momo_fdvs.security.passwords import hash_password
from momo_fdvs.services.audit import audit_event
from momo_fdvs.services.auth import AuthFailure


def admin_projection(user: User) -> dict[str, object]:
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "email": str(user.email),
        "phone_e164": user.phone_e164,
        "roles": sorted(user_roles(user.id)),
        "status": user.status,
        "must_change_password": user.must_change_password,
        "version": user.updated_at.isoformat(),
    }


def _require_user(user_id: uuid.UUID) -> User:
    user = db.session.get(User, user_id)
    if user is None:
        raise AuthFailure("USER_NOT_FOUND", "The user was not found.", 404)
    return user


def _check_version(user: User, expected: str) -> None:
    if user.updated_at.isoformat() != expected:
        raise AuthFailure(
            "VERSION_CONFLICT",
            "The user changed since it was loaded. Refresh and try again.",
            409,
        )


def _active_admin_count() -> int:
    return int(
        db.session.scalar(
            select(func.count(User.id))
            .join(UserRole, UserRole.user_id == User.id)
            .where(User.status == "ACTIVE", UserRole.role_code == "ADMIN")
        )
        or 0
    )


def list_users(filters: dict[str, Any]) -> tuple[list[User], int]:
    statement = select(User)
    count_statement = select(func.count(func.distinct(User.id))).select_from(User)
    if filters.get("role"):
        statement = statement.join(UserRole, UserRole.user_id == User.id)
        count_statement = count_statement.join(UserRole, UserRole.user_id == User.id)
        statement = statement.where(UserRole.role_code == filters["role"])
        count_statement = count_statement.where(UserRole.role_code == filters["role"])
    if filters.get("status"):
        statement = statement.where(User.status == filters["status"])
        count_statement = count_statement.where(User.status == filters["status"])
    if search := filters.get("search"):
        pattern = f"%{search.strip()}%"
        search_clause = or_(User.email.ilike(pattern), User.full_name.ilike(pattern))
        statement = statement.where(search_clause)
        count_statement = count_statement.where(search_clause)
    page = filters["page"]
    page_size = filters["page_size"]
    users = list(
        db.session.scalars(
            statement.distinct()
            .order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return users, int(db.session.scalar(count_statement) or 0)


def create_user(data: dict[str, Any], actor: User, actor_roles: set[str]) -> User:
    normalized_email = data["email"].strip().lower()
    if db.session.scalar(select(User.id).where(User.email == normalized_email)) is not None:
        raise AuthFailure("ACCOUNT_EXISTS", "An account with that email already exists.", 409)
    requested_roles = set(data["roles"])
    if len(
        db.session.scalars(select(Role.code).where(Role.code.in_(requested_roles))).all()
    ) != len(requested_roles):
        raise AuthFailure("INVALID_ROLE", "One or more roles are invalid.", 422)
    now = datetime.now(UTC)
    user = User(
        email=normalized_email,
        full_name=data["full_name"].strip(),
        phone_e164=data.get("phone_e164"),
        password_hash=hash_password(data["password"]),
        status="ACTIVE",
        password_changed_at=now,
        must_change_password=True,
    )
    db.session.add(user)
    db.session.flush()
    for role in requested_roles:
        db.session.add(
            UserRole(user_id=user.id, role_code=role, granted_by=actor.id, granted_at=now)
        )
    audit_event(
        "admin.user_created",
        "SUCCESS",
        actor_id=actor.id,
        roles=actor_roles,
        target_id=user.id,
        metadata={"roles": sorted(requested_roles)},
    )
    db.session.commit()
    return user


def update_user(
    user_id: uuid.UUID,
    data: dict[str, Any],
    actor: User,
    actor_roles: set[str],
) -> User:
    user = _require_user(user_id)
    _check_version(user, data["expected_version"])
    new_status = data.get("status", user.status)
    if user.id == actor.id and new_status != "ACTIVE":
        raise AuthFailure("SELF_LOCKOUT_PREVENTED", "You cannot disable your own account.", 409)
    if (
        user.status == "ACTIVE"
        and new_status != "ACTIVE"
        and "ADMIN" in user_roles(user.id)
        and _active_admin_count() <= 1
    ):
        raise AuthFailure("LAST_ADMIN_PROTECTED", "The last active admin cannot be disabled.", 409)
    if "full_name" in data:
        user.full_name = data["full_name"].strip()
    if "phone_e164" in data:
        user.phone_e164 = data["phone_e164"]
    if new_status != user.status:
        user.status = new_status
        user.token_version += 1
        revoke_user_sessions(user.id, actor, actor_roles, commit=False)
    audit_event(
        "admin.user_updated",
        "SUCCESS",
        actor_id=actor.id,
        roles=actor_roles,
        target_id=user.id,
        metadata={"status": user.status},
    )
    db.session.commit()
    return user


def replace_roles(
    user_id: uuid.UUID,
    roles: set[str],
    expected_version: str,
    actor: User,
    actor_roles: set[str],
) -> User:
    user = _require_user(user_id)
    _check_version(user, expected_version)
    current = user_roles(user.id)
    if user.id == actor.id and "ADMIN" not in roles:
        raise AuthFailure("SELF_LOCKOUT_PREVENTED", "You cannot remove your own admin role.", 409)
    if (
        "ADMIN" in current
        and "ADMIN" not in roles
        and user.status == "ACTIVE"
        and _active_admin_count() <= 1
    ):
        raise AuthFailure(
            "LAST_ADMIN_PROTECTED", "The last active admin role cannot be removed.", 409
        )
    if len(db.session.scalars(select(Role.code).where(Role.code.in_(roles))).all()) != len(roles):
        raise AuthFailure("INVALID_ROLE", "One or more roles are invalid.", 422)
    db.session.query(UserRole).filter(UserRole.user_id == user.id).delete()
    now = datetime.now(UTC)
    for role in roles:
        db.session.add(
            UserRole(user_id=user.id, role_code=role, granted_by=actor.id, granted_at=now)
        )
    user.token_version += 1
    revoke_user_sessions(user.id, actor, actor_roles, commit=False)
    audit_event(
        "admin.roles_replaced",
        "SUCCESS",
        actor_id=actor.id,
        roles=actor_roles,
        target_id=user.id,
        metadata={"before": sorted(current), "after": sorted(roles)},
    )
    db.session.commit()
    return user


def revoke_user_sessions(
    user_id: uuid.UUID,
    actor: User,
    actor_roles: set[str],
    *,
    commit: bool = True,
) -> User:
    user = _require_user(user_id)
    now = datetime.now(UTC)
    db.session.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=now, revoke_reason="ADMIN_REVOKED")
    )
    audit_event(
        "admin.sessions_revoked",
        "SUCCESS",
        actor_id=actor.id,
        roles=actor_roles,
        target_id=user.id,
        metadata={"reason": "ADMIN_REVOKED"},
    )
    if commit:
        db.session.commit()
    return user
