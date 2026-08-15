from __future__ import annotations

import io
import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from flask import Flask
from PIL import Image
from sqlalchemy import select

from momo_fdvs.extensions import db
from momo_fdvs.models import (
    FraudCase,
    FraudRuleSet,
    Notification,
    OCRConfirmation,
    OCRResult,
    ReferenceImportBatch,
    ReferenceTransaction,
    Role,
    Transaction,
    User,
    UserRole,
)
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


def _png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (96, 160), color=(245, 247, 240)).save(output, format="PNG")
    return output.getvalue()


def _register(client: Any, name: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": name,
            "email": f"analysis-api-{uuid.uuid4()}@example.test",
            "password": TEST_CREDENTIAL,
        },
        headers={"X-Client-Type": "mobile"},
    )
    assert response.status_code == 201
    return response.json["data"]


def _headers(session: dict[str, Any], key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def _staff(app: Flask, client: Any, role: str) -> tuple[dict[str, Any], uuid.UUID]:
    email = f"analysis-{role.lower()}-{uuid.uuid4()}@example.test"
    with app.app_context():
        user = User(
            email=email,
            password_hash=hash_password(TEST_CREDENTIAL),
            full_name=f"Analysis {role.title()}",
            status="ACTIVE",
            password_changed_at=datetime.now(UTC),
        )
        db.session.add(user)
        db.session.flush()
        user_id = user.id
        db.session.add(UserRole(user_id=user.id, role_code=role, granted_at=datetime.now(UTC)))
        db.session.commit()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": TEST_CREDENTIAL},
        headers={"X-Client-Type": "mobile"},
    )
    assert response.status_code == 200
    return response.json["data"], user_id


def _upload(client: Any, session: dict[str, Any]) -> uuid.UUID:
    response = client.post(
        "/api/v1/transactions",
        data={
            "receipt": (io.BytesIO(_png()), "analysis.png", "image/png"),
            "source": "GALLERY",
        },
        headers=_headers(session, f"upload-{uuid.uuid4()}"),
        content_type="multipart/form-data",
    )
    assert response.status_code == 201, response.get_data(as_text=True)
    return uuid.UUID(response.json["data"]["transaction"]["id"])


def _seed_confirmation(app: Flask, transaction_id: uuid.UUID, owner_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    token = uuid.uuid4().hex
    reference = f"A{token[:11].upper()}"
    with app.app_context():
        transaction = db.session.get(Transaction, transaction_id)
        owner = db.session.get(User, owner_id)
        assert transaction is not None and transaction.receipt is not None and owner is not None
        ocr = OCRResult(
            receipt_id=transaction.receipt.id,
            engine_name="tesseract",
            engine_version="controlled",
            pipeline_version="ocr-pipeline-v1",
            selected_variant="original",
            raw_text="controlled API fixture",
            token_data=[],
            extracted_fields={
                "amount": {"value": "125.00", "confidence": 0.95},
                "transaction_reference": {"value": reference, "confidence": 0.96},
            },
            field_confidences={"amount": 0.95, "transaction_reference": 0.96},
            warnings=[],
            required_field_accuracy_hint=Decimal("0.95"),
        )
        db.session.add(ocr)
        db.session.flush()
        confirmation = OCRConfirmation(
            ocr_result_id=ocr.id,
            transaction_id=transaction.id,
            confirmed_fields={
                "provider_code": "MTN_MOMO",
                "transaction_reference": reference,
                "amount": "125.00",
                "currency": "GHS",
                "sender_name": "Controlled Sender",
                "sender_phone": "+233240000002",
                "receiver_name": "Controlled Receiver",
                "receiver_phone": "+233240000001",
                "occurred_at": "2026-08-08T14:30:00Z",
                "status_text": "SUCCESSFUL",
            },
            corrections=[],
            confirmed_by=owner.id,
            confirmed_at=now,
            schema_version="ocr-fields-v1",
        )
        batch = ReferenceImportBatch(
            source_label=f"analysis-api-{token}",
            original_filename="controlled.csv",
            file_sha256=token * 2,
            status="COMMITTED",
            total_rows=1,
            valid_rows=1,
            invalid_rows=0,
            uploaded_by=owner.id,
        )
        rule_set = db.session.scalar(select(FraudRuleSet).where(FraudRuleSet.status == "ACTIVE"))
        if rule_set is None:
            db.session.add(
                FraudRuleSet(
                    version="demo-1",
                    status="ACTIVE",
                    risk_weights={},
                    thresholds={},
                    description="Controlled PR18 analysis API anchor.",
                    created_by=owner.id,
                    activated_by=owner.id,
                    activated_at=now,
                    row_version=1,
                )
            )
        db.session.add_all([confirmation, batch])
        db.session.flush()
        db.session.add(
            ReferenceTransaction(
                import_batch_id=batch.id,
                provider_code="MTN_MOMO",
                transaction_reference=reference,
                amount=Decimal("125.00"),
                currency="GHS",
                sender_name_normalised="CONTROLLED SENDER",
                sender_phone_e164="+233240000002",
                receiver_name_normalised="CONTROLLED RECEIVER",
                receiver_phone_e164="+233240000001",
                occurred_at=datetime(2026, 8, 8, 14, 30, tzinfo=UTC),
                transaction_status="SUCCESSFUL",
                raw_row={"controlled_fixture": True},
            )
        )
        transaction.status = "READY"
        db.session.commit()


def test_start_replay_poll_and_owner_visibility(app: Flask) -> None:
    client = app.test_client()
    owner = _register(client, "Analysis Owner")
    outsider = _register(client, "Analysis Outsider")
    transaction_id = _upload(client, owner)
    _seed_confirmation(app, transaction_id, uuid.UUID(owner["user"]["id"]))

    missing_key = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses", headers=_headers(owner)
    )
    assert missing_key.status_code == 400
    assert missing_key.json["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    key = f"analysis-{uuid.uuid4()}"
    created = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses",
        headers=_headers(owner, key),
    )
    assert created.status_code == 202, created.get_data(as_text=True)
    data = created.json["data"]
    run_id = data["analysis_run_id"]
    assert data["poll_url"] == f"/api/v1/analyses/{run_id}"
    assert data["replayed"] is False

    replay = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses",
        headers=_headers(owner, key),
    )
    assert replay.status_code == 202
    assert replay.json["data"]["analysis_run_id"] == run_id
    assert replay.json["data"]["replayed"] is True

    with app.app_context():
        notifications = db.session.scalars(
            select(Notification).where(
                Notification.user_id == uuid.UUID(owner["user"]["id"]),
                Notification.target_id == uuid.UUID(run_id),
            )
        ).all()
        assert len(notifications) == 1
        assert notifications[0].type == "ANALYSIS_COMPLETED"

    detail = client.get(f"/api/v1/analyses/{run_id}", headers=_headers(owner))
    assert detail.status_code == 200, detail.get_data(as_text=True)
    projection = detail.json["data"]
    assert set(projection) >= {
        "id",
        "status",
        "risk",
        "verification",
        "evidence_summary",
        "versions",
        "progress",
    }
    assert projection["risk"]["score"] is None
    assert projection["risk"]["band"] == "inconclusive"
    assert projection["risk"]["disclaimer"] == (
        "This is an automated risk assessment, not a final legal determination."
    )
    assert projection["ocr_review"] == {
        "confirmed_field_count": 10,
        "correction_count": 0,
        "schema_version": "ocr-fields-v1",
    }
    assert projection["verification"]["status"] == "VERIFIED"
    assert "storage" not in detail.get_data(as_text=True).lower()

    denied = client.get(f"/api/v1/analyses/{run_id}", headers=_headers(outsider))
    assert denied.status_code == 404

    evidence = client.get(f"/api/v1/analyses/{run_id}/evidence", headers=_headers(owner))
    assert evidence.status_code == 200
    assert evidence.json["data"]["risk"] == projection["risk"]


def test_unassigned_staff_cannot_read_owner_analysis_or_evidence(app: Flask) -> None:
    client = app.test_client()
    owner = _register(client, "Scoped Analysis Owner")
    transaction_id = _upload(client, owner)
    _seed_confirmation(app, transaction_id, uuid.UUID(owner["user"]["id"]))
    started = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses",
        headers=_headers(owner, f"analysis-{uuid.uuid4()}"),
    )
    assert started.status_code == 202
    run_id = started.json["data"]["analysis_run_id"]

    for role in ("ADMIN", "INVESTIGATOR"):
        staff, _staff_id = _staff(app, client, role)
        assert client.get(f"/api/v1/analyses/{run_id}", headers=_headers(staff)).status_code == 404
        assert (
            client.get(f"/api/v1/analyses/{run_id}/evidence", headers=_headers(staff)).status_code
            == 404
        )


def test_assigned_investigator_can_read_analysis_and_evidence(app: Flask) -> None:
    client = app.test_client()
    owner = _register(client, "Assigned Analysis Owner")
    transaction_id = _upload(client, owner)
    _seed_confirmation(app, transaction_id, uuid.UUID(owner["user"]["id"]))
    started = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses",
        headers=_headers(owner, f"analysis-{uuid.uuid4()}"),
    )
    assert started.status_code == 202
    run_id = started.json["data"]["analysis_run_id"]
    investigator, investigator_id = _staff(app, client, "INVESTIGATOR")
    with app.app_context():
        db.session.add(
            FraudCase(
                transaction_id=transaction_id,
                source="ADMIN",
                category="CONTROLLED_REVIEW",
                status="ASSIGNED",
                assigned_to=investigator_id,
                opened_at=datetime.now(UTC),
            )
        )
        db.session.commit()

    assert (
        client.get(f"/api/v1/analyses/{run_id}", headers=_headers(investigator)).status_code == 200
    )
    assert (
        client.get(
            f"/api/v1/analyses/{run_id}/evidence", headers=_headers(investigator)
        ).status_code
        == 200
    )


def test_completed_transaction_allows_replay_and_new_reanalysis(app: Flask) -> None:
    client = app.test_client()
    owner = _register(client, "Terminal Reanalysis Owner")
    transaction_id = _upload(client, owner)
    _seed_confirmation(app, transaction_id, uuid.UUID(owner["user"]["id"]))
    first_key = f"analysis-{uuid.uuid4()}"
    first = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses",
        headers=_headers(owner, first_key),
    )
    assert first.status_code == 202
    first_run_id = first.json["data"]["analysis_run_id"]
    with app.app_context():
        transaction = db.session.get(Transaction, transaction_id)
        assert transaction is not None
        transaction.status = "COMPLETED"
        db.session.commit()

    replay = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses",
        headers=_headers(owner, first_key),
    )
    assert replay.status_code == 202
    assert replay.json["data"]["analysis_run_id"] == first_run_id
    assert replay.json["data"]["replayed"] is True

    rerun = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses",
        headers=_headers(owner, f"analysis-{uuid.uuid4()}"),
    )
    assert rerun.status_code == 202
    assert rerun.json["data"]["analysis_run_id"] != first_run_id
    assert rerun.json["data"]["replayed"] is False


def test_start_requires_confirmed_ocr(app: Flask) -> None:
    client = app.test_client()
    owner = _register(client, "Unreviewed Owner")
    transaction_id = _upload(client, owner)

    response = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses",
        headers=_headers(owner, f"analysis-{uuid.uuid4()}"),
    )

    assert response.status_code == 409
    assert response.json["error"]["code"] == "OCR_REVIEW_REQUIRED"


def test_invalid_policy_returns_safe_configuration_failure(
    app: Flask, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client = app.test_client()
    owner = _register(client, "Policy Failure Owner")
    transaction_id = _upload(client, owner)
    _seed_confirmation(app, transaction_id, uuid.UUID(owner["user"]["id"]))
    invalid_policy = tmp_path / "private-policy-location.json"
    invalid_policy.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("momo_fdvs.services.analysis_orchestrator._POLICY_PATH", invalid_policy)

    response = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses",
        headers=_headers(owner, f"analysis-{uuid.uuid4()}"),
    )

    assert response.status_code == 503
    assert response.json["error"]["code"] == "RISK_POLICY_SCHEMA_INVALID"
    assert str(invalid_policy) not in response.get_data(as_text=True)
