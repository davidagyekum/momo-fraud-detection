"""Central authentication, role and ownership policies."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar, cast

from flask import current_app, g, request
from sqlalchemy import select

from momo_fdvs.errors import error_response
from momo_fdvs.extensions import db
from momo_fdvs.models import Transaction, User, UserRole
from momo_fdvs.security.tokens import InvalidAccessToken, decode_access_token

P = ParamSpec("P")
R = TypeVar("R")


def user_roles(user_id: uuid.UUID) -> set[str]:
    return set(
        db.session.scalars(select(UserRole.role_code).where(UserRole.user_id == user_id)).all()
    )


def authenticate_request() -> tuple[User, set[str]] | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        claims = decode_access_token(header[7:], current_app.config["JWT_ACCESS_SECRET"])
    except InvalidAccessToken:
        return None
    user = db.session.get(User, claims.user_id)
    roles = user_roles(claims.user_id)
    if (
        user is None
        or user.status != "ACTIVE"
        or user.token_version != claims.token_version
        or roles != set(claims.roles)
    ):
        return None
    return user, roles


def require_auth(function: Callable[P, R]) -> Callable[P, R]:  # noqa: UP047
    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        authenticated = authenticate_request()
        if authenticated is None:
            return cast(
                R, error_response("AUTHENTICATION_REQUIRED", "Authentication is required.", 401)
            )
        g.current_user, g.current_roles = authenticated
        return function(*args, **kwargs)

    return wrapped


def require_roles(*required: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        @require_auth
        @wraps(function)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            if not set(required) & set(g.current_roles):
                return cast(R, error_response("PERMISSION_DENIED", "Permission is denied.", 403))
            return function(*args, **kwargs)

        return wrapped

    return decorator


def owned_transaction(transaction_id: uuid.UUID) -> Transaction | None:
    transaction = db.session.get(Transaction, transaction_id)
    if transaction is None or transaction.user_id != g.current_user.id:
        return None
    return transaction
