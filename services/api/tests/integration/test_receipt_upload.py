from __future__ import annotations

import io
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from flask import Flask
from PIL import Image
from sqlalchemy import select

from momo_fdvs.extensions import db
from momo_fdvs.models import AuditLog, Role, Transaction, User, UserRole
from momo_fdvs.security.passwords import hash_password
from momo_fdvs.services.receipts import ReceiptFailure, inspect_receipt, store_receipt
from momo_fdvs.storage.local import LocalPrivateStorage

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


def _png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (640, 480), "white").save(output, format="PNG")
    return output.getvalue()


def _register(client: Any) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Receipt Owner",
            "email": f"receipt-{uuid.uuid4()}@example.test",
            "password": TEST_CREDENTIAL,
        },
        headers={"X-Client-Type": "mobile"},
    )
    assert response.status_code == 201
    return response.json["data"]


def _headers(session: dict[str, Any], key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    if key:
        headers["Idempotency-Key"] = key
    return headers


def _multipart(content: bytes | None = None, filename: str = "receipt.png") -> dict[str, Any]:
    return {
        "receipt": (io.BytesIO(content or _png()), filename, "application/octet-stream"),
        "source": "GALLERY",
        "client_metadata": '{"platform":"test"}',
    }


def test_upload_replay_private_reads_and_owner_isolation(app: Flask) -> None:
    client = app.test_client()
    owner = _register(client)
    key = f"upload-{uuid.uuid4()}"
    created = client.post(
        "/api/v1/transactions",
        data=_multipart(),
        headers=_headers(owner, key),
        content_type="multipart/form-data",
    )
    assert created.status_code == 201, created.get_data(as_text=True)
    body = created.json["data"]
    assert body["transaction"]["status"] == "UPLOADED"
    assert body["receipt"]["media_type"] == "image/png"
    assert body["next_action"]["type"] == "RUN_OCR"
    assert "object_key" not in created.get_data(as_text=True)

    replay = client.post(
        "/api/v1/transactions",
        data=_multipart(),
        headers=_headers(owner, key),
        content_type="multipart/form-data",
    )
    assert replay.status_code == 200
    assert replay.json["data"]["replayed"] is True
    assert replay.json["data"]["transaction"]["id"] == body["transaction"]["id"]

    duplicate = client.post(
        "/api/v1/transactions",
        data=_multipart(),
        headers=_headers(owner, f"upload-{uuid.uuid4()}"),
        content_type="multipart/form-data",
    )
    assert duplicate.status_code == 201
    assert duplicate.json["data"]["receipt"]["duplicate_warning"]["exact_match_found"]
    duplicate_text = duplicate.get_data(as_text=True)
    assert "object_key" not in duplicate_text
    assert "owner_id" not in duplicate_text

    transaction_id = body["transaction"]["id"]
    thumbnail = client.get(
        f"/api/v1/transactions/{transaction_id}/receipt?variant=thumbnail",
        headers=_headers(owner),
    )
    assert thumbnail.status_code == 200
    assert thumbnail.content_type == "image/jpeg"
    assert thumbnail.headers["Cache-Control"].startswith("private, no-store")
    assert thumbnail.headers["X-Content-Type-Options"] == "nosniff"

    outsider = _register(client)
    denied = client.get(
        f"/api/v1/transactions/{transaction_id}/receipt?variant=original",
        headers=_headers(outsider),
    )
    assert denied.status_code == 404

    with app.app_context():
        transaction = db.session.get(Transaction, uuid.UUID(transaction_id))
        assert transaction is not None and transaction.receipt is not None
        assert transaction.receipt.sha256
        actions = set(
            db.session.scalars(
                select(AuditLog.action).where(AuditLog.target_id == transaction.id)
            ).all()
        )
        assert {"receipt.uploaded", "receipt.upload_replayed", "receipt.viewed"} <= actions
        assert "receipt.access_denied" in actions


def test_requires_auth_idempotency_and_rejects_key_reuse(app: Flask) -> None:
    client = app.test_client()
    assert client.post("/api/v1/transactions", data=_multipart()).status_code == 401
    owner = _register(client)
    missing = client.post(
        "/api/v1/transactions",
        data=_multipart(),
        headers=_headers(owner),
        content_type="multipart/form-data",
    )
    assert missing.status_code == 400
    assert missing.json["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    key = f"upload-{uuid.uuid4()}"
    first = client.post(
        "/api/v1/transactions",
        data=_multipart(),
        headers=_headers(owner, key),
        content_type="multipart/form-data",
    )
    assert first.status_code == 201
    different = io.BytesIO()
    Image.new("RGB", (641, 480), "black").save(different, format="PNG")
    conflict = client.post(
        "/api/v1/transactions",
        data=_multipart(different.getvalue()),
        headers=_headers(owner, key),
        content_type="multipart/form-data",
    )
    assert conflict.status_code == 409
    assert conflict.json["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_user_filename_never_controls_storage_path(app: Flask) -> None:
    client = app.test_client()
    owner = _register(client)
    response = client.post(
        "/api/v1/transactions",
        data=_multipart(filename="../../private/receipt.png"),
        headers=_headers(owner, f"upload-{uuid.uuid4()}"),
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    transaction_id = uuid.UUID(response.json["data"]["transaction"]["id"])
    with app.app_context():
        receipt = db.session.get(Transaction, transaction_id).receipt
        assert receipt is not None
        assert receipt.original_filename == "receipt.png"
        assert "private/receipt.png" not in receipt.object_key


def test_staff_can_read_without_receipt_identity_leak(app: Flask) -> None:
    client = app.test_client()
    owner = _register(client)
    created = client.post(
        "/api/v1/transactions",
        data=_multipart(),
        headers=_headers(owner, f"upload-{uuid.uuid4()}"),
        content_type="multipart/form-data",
    )
    transaction_id = created.json["data"]["transaction"]["id"]

    email = f"investigator-{uuid.uuid4()}@example.test"
    with app.app_context():
        investigator = User(
            email=email,
            password_hash=hash_password(TEST_CREDENTIAL),
            full_name="Investigator",
            status="ACTIVE",
            password_changed_at=datetime.now(UTC),
        )
        db.session.add(investigator)
        db.session.flush()
        db.session.add(
            UserRole(
                user_id=investigator.id,
                role_code="INVESTIGATOR",
                granted_at=datetime.now(UTC),
            )
        )
        db.session.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": TEST_CREDENTIAL},
        headers={"X-Client-Type": "mobile"},
    ).json["data"]
    response = client.get(
        f"/api/v1/transactions/{transaction_id}/receipt?variant=original",
        headers=_headers(login),
    )
    assert response.status_code == 200


class FailingStorage(LocalPrivateStorage):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.put_count = 0
        self.deleted: list[str] = []

    def put_bytes(
        self,
        key: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ):
        self.put_count += 1
        if self.put_count == 2:
            raise OSError("controlled derivative failure")
        return super().put_bytes(key, content, content_type, metadata)

    def delete(self, key: str) -> None:
        self.deleted.append(key)
        super().delete(key)


def test_storage_failure_rolls_back_database_and_original(app: Flask, tmp_path: Path) -> None:
    storage = FailingStorage(tmp_path / "failing-private")
    app.extensions["object_storage"] = storage
    client = app.test_client()
    owner = _register(client)
    response = client.post(
        "/api/v1/transactions",
        data=_multipart(),
        headers=_headers(owner, f"upload-{uuid.uuid4()}"),
        content_type="multipart/form-data",
    )
    assert response.status_code == 503
    assert response.json["error"]["code"] == "RECEIPT_STORAGE_UNAVAILABLE"
    assert len(storage.deleted) == 1
    assert not any((tmp_path / "failing-private").rglob("*.png"))
    with app.app_context():
        owner_id = uuid.UUID(owner["user"]["id"])
        assert db.session.scalar(select(Transaction).where(Transaction.user_id == owner_id)) is None


def test_database_failure_cleans_both_written_objects(
    app: Flask, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = app.test_client()
    owner_session = _register(client)
    storage = LocalPrivateStorage(tmp_path / "database-failure-private")
    with app.app_context():
        owner_id = uuid.UUID(owner_session["user"]["id"])
        owner = db.session.get(User, owner_id)
        assert owner is not None
        inspected = inspect_receipt(_png(), "receipt.png")

        def fail_commit() -> None:
            raise OSError("controlled database commit failure")

        monkeypatch.setattr(db.session, "commit", fail_commit)
        with pytest.raises(ReceiptFailure) as raised:
            store_receipt(
                user=owner,
                roles={"USER"},
                inspected=inspected,
                source="GALLERY",
                captured_at=None,
                client_metadata={},
                idempotency_key=f"upload-{uuid.uuid4()}",
                storage=storage,
            )
        assert raised.value.status == 503
        assert not any((tmp_path / "database-failure-private").rglob("*.*"))
