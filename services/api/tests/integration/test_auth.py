from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from flask import Flask, g

from momo_fdvs import create_app
from momo_fdvs.extensions import db
from momo_fdvs.models import Role, Transaction, User, UserRole
from momo_fdvs.policies.auth import owned_transaction
from momo_fdvs.security.passwords import hash_password

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="requires an isolated PostgreSQL test database",
)

TEST_CREDENTIAL = "Correct-Horse-Battery-7"


@pytest.fixture(autouse=True)
def roles(app: Flask) -> None:
    with app.app_context():
        for code in ("USER", "ADMIN", "INVESTIGATOR"):
            if db.session.get(Role, code) is None:
                db.session.add(Role(code=code, description=f"Test {code}"))
        db.session.commit()


def _email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}@example.test"


def _register(client: Any, email: str | None = None) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": email or _email("user"),
            "password": TEST_CREDENTIAL,
        },
        headers={"X-Client-Type": "mobile"},
    )
    assert response.status_code == 201, response.get_data(as_text=True)
    return response.json["data"]


def _admin(app: Flask) -> tuple[str, uuid.UUID]:
    email = _email("admin")
    with app.app_context():
        user = User(
            email=email,
            password_hash=hash_password(TEST_CREDENTIAL),
            full_name="Test Admin",
            status="ACTIVE",
            password_changed_at=datetime.now(UTC),
        )
        db.session.add(user)
        db.session.flush()
        db.session.add(
            UserRole(
                user_id=user.id,
                role_code="ADMIN",
                granted_by=None,
                granted_at=datetime.now(UTC),
            )
        )
        db.session.commit()
        return email, user.id


def _mobile_login(client: Any, email: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": TEST_CREDENTIAL},
        headers={"X-Client-Type": "mobile"},
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    return response.json["data"]


def test_register_login_me_profile_and_password_change(app: Flask) -> None:
    client = app.test_client()
    email = _email("profile")
    session = _register(client, email)
    assert session["user"]["roles"] == ["USER"]
    assert session["refresh_token"]
    assert session["csrf_token"]

    headers = {"Authorization": f"Bearer {session['access_token']}"}
    me = client.get("/api/v1/me", headers=headers)
    assert me.status_code == 200
    assert me.json["data"]["email"] == email

    updated = client.patch(
        "/api/v1/me",
        json={"full_name": "Updated Name", "phone_e164": "+233200000001"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json["data"]["full_name"] == "Updated Name"
    assert client.get("/api/v1/me").status_code == 401

    wrong = client.post(
        "/api/v1/me/change-password",
        json={"current_password": "wrong-password", "new_password": "New-Correct-Password-8"},
        headers=headers,
    )
    assert wrong.status_code == 400
    changed = client.post(
        "/api/v1/me/change-password",
        json={
            "current_password": TEST_CREDENTIAL,
            "new_password": "New-Correct-Password-8",
        },
        headers=headers,
    )
    assert changed.status_code == 200
    assert client.get("/api/v1/me", headers=headers).status_code == 401


def test_invalid_login_refresh_rotation_reuse_and_logout(app: Flask) -> None:
    client = app.test_client()
    email = _email("refresh")
    first = _register(client, email)
    invalid = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "definitely-wrong"}
    )
    assert invalid.status_code == 401
    assert invalid.json["error"]["code"] == "INVALID_CREDENTIALS"

    rotated_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
        headers={"X-Client-Type": "mobile"},
    )
    assert rotated_response.status_code == 200, rotated_response.get_data(as_text=True)
    second = rotated_response.json["data"]
    assert second["refresh_token"] != first["refresh_token"]

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert reused.status_code == 401
    assert reused.json["error"]["code"] == "REFRESH_REUSE_DETECTED"
    family_revoked = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": second["refresh_token"]}
    )
    assert family_revoked.status_code == 401

    fresh = _mobile_login(client, email)
    logout = client.post("/api/v1/auth/logout", json={"refresh_token": fresh["refresh_token"]})
    assert logout.status_code == 200
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": fresh["refresh_token"]}
        ).status_code
        == 401
    )


def test_web_refresh_requires_bound_double_submit_csrf(app: Flask) -> None:
    client = app.test_client()
    email = _email("cookie")
    _register(client, email)
    response = client.post("/api/v1/auth/login", json={"email": email, "password": TEST_CREDENTIAL})
    assert response.status_code == 200
    cookies = "\n".join(response.headers.getlist("Set-Cookie"))
    assert "momo_fdvs_refresh=" in cookies
    assert "HttpOnly" in cookies
    assert "SameSite=Lax" in cookies
    assert any(
        header.startswith("momo_fdvs_csrf=") and "Path=/;" in header
        for header in response.headers.getlist("Set-Cookie")
    )
    assert response.json["data"]["refresh_token"] is None

    assert client.post("/api/v1/auth/refresh", json={}).status_code == 401
    csrf_cookie = client.get_cookie("momo_fdvs_csrf", path="/")
    assert csrf_cookie is not None
    refreshed = client.post(
        "/api/v1/auth/refresh", json={}, headers={"X-CSRF-Token": csrf_cookie.value}
    )
    assert refreshed.status_code == 200, refreshed.get_data(as_text=True)


def test_password_reset_is_generic_single_use_and_revokes_tokens(app: Flask) -> None:
    client = app.test_client()
    email = _email("reset")
    session = _register(client, email)
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": _email("unknown")})
    known = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert unknown.status_code == known.status_code == 202
    assert unknown.json["data"] == known.json["data"] == {"accepted": True}
    token = app.extensions["password_reset_outbox"][-1]["token"]
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "Reset-Correct-Password-9"},
    )
    assert reset.status_code == 200
    assert (
        client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "Another-Correct-Password-0"},
        ).status_code
        == 400
    )
    assert (
        client.get(
            "/api/v1/me", headers={"Authorization": f"Bearer {session['access_token']}"}
        ).status_code
        == 401
    )


def test_admin_rbac_user_management_and_safeguards(app: Flask) -> None:
    client = app.test_client()
    normal = _register(client)
    denied = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {normal['access_token']}"},
    )
    assert denied.status_code == 403

    admin_email, admin_id = _admin(app)
    admin_session = _mobile_login(client, admin_email)
    headers = {"Authorization": f"Bearer {admin_session['access_token']}"}
    created = client.post(
        "/api/v1/admin/users",
        json={
            "full_name": "Test Investigator",
            "email": _email("investigator"),
            "password": TEST_CREDENTIAL,
            "roles": ["INVESTIGATOR"],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.get_data(as_text=True)
    target = created.json["data"]
    listed = client.get(
        "/api/v1/admin/users", query_string={"role": "INVESTIGATOR"}, headers=headers
    )
    assert listed.status_code == 200
    assert listed.json["data"]["total"] >= 1

    roles_changed = client.put(
        f"/api/v1/admin/users/{target['id']}/roles",
        json={"roles": ["USER", "INVESTIGATOR"], "expected_version": target["version"]},
        headers=headers,
    )
    assert roles_changed.status_code == 200, roles_changed.get_data(as_text=True)
    current = roles_changed.json["data"]
    stale = client.patch(
        f"/api/v1/admin/users/{target['id']}",
        json={"status": "DISABLED", "expected_version": target["version"]},
        headers=headers,
    )
    assert stale.status_code == 409
    updated = client.patch(
        f"/api/v1/admin/users/{target['id']}",
        json={"status": "DISABLED", "expected_version": current["version"]},
        headers=headers,
    )
    assert updated.status_code == 200

    admin_detail = next(
        user
        for user in client.get(
            "/api/v1/admin/users", query_string={"search": admin_email}, headers=headers
        ).json["data"]["users"]
        if user["id"] == str(admin_id)
    )
    self_lockout = client.put(
        f"/api/v1/admin/users/{admin_id}/roles",
        json={"roles": ["USER"], "expected_version": admin_detail["version"]},
        headers=headers,
    )
    assert self_lockout.status_code == 409
    assert (
        client.post(
            f"/api/v1/admin/users/{target['id']}/revoke-sessions", headers=headers
        ).status_code
        == 200
    )


def test_ownership_policy_hides_another_users_transaction(app: Flask) -> None:
    with app.app_context():
        first = User(
            email=_email("owner"),
            password_hash=hash_password(TEST_CREDENTIAL),
            full_name="Owner",
            status="ACTIVE",
            password_changed_at=datetime.now(UTC),
        )
        second = User(
            email=_email("other"),
            password_hash=hash_password(TEST_CREDENTIAL),
            full_name="Other",
            status="ACTIVE",
            password_changed_at=datetime.now(UTC),
        )
        db.session.add_all([first, second])
        db.session.flush()
        transaction = Transaction(user_id=first.id, status="UPLOADED")
        db.session.add(transaction)
        db.session.commit()
        transaction_id = transaction.id
        with app.test_request_context():
            g.current_user = first
            assert owned_transaction(transaction_id) is not None
            g.current_user = second
            assert owned_transaction(transaction_id) is None
            assert owned_transaction(uuid.uuid4()) is None


def test_login_rate_limit_returns_standard_envelope(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    monkeypatch.setenv("RATE_LIMIT_LOGIN", "2 per minute")
    monkeypatch.setenv("LOCAL_PRIVATE_STORAGE_ROOT", str(tmp_path / "private"))
    application = create_app("testing")
    client = application.test_client()
    responses = [
        client.post(
            "/api/v1/auth/login",
            json={"email": _email("limited"), "password": "wrong-password"},
            environ_base={"REMOTE_ADDR": "198.51.100.23"},
        )
        for _ in range(3)
    ]
    assert [response.status_code for response in responses] == [401, 401, 429]
    assert responses[-1].json["error"]["code"] == "RATE_LIMITED"
