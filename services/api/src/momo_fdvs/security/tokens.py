"""Signed access tokens and hashed opaque token helpers."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt


class InvalidAccessToken(ValueError):
    pass


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    roles: frozenset[str]
    token_version: int


def opaque_token() -> str:
    return secrets.token_urlsafe(48)


def token_hash(token: str, secret: str) -> str:
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def encode_access_token(
    *, user_id: uuid.UUID, roles: set[str], token_version: int, secret: str, ttl_minutes: int
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "roles": sorted(roles),
            "ver": token_version,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=ttl_minutes),
            "jti": str(uuid.uuid4()),
        },
        secret,
        algorithm="HS256",
    )


def decode_access_token(token: str, secret: str) -> AccessClaims:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["sub", "roles", "ver", "type", "iat", "exp", "jti"]},
        )
        if payload["type"] != "access" or not isinstance(payload["roles"], list):
            raise InvalidAccessToken("invalid access token claims")
        return AccessClaims(
            user_id=uuid.UUID(payload["sub"]),
            roles=frozenset(str(role) for role in payload["roles"]),
            token_version=int(payload["ver"]),
        )
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise InvalidAccessToken("access token is invalid or expired") from exc
