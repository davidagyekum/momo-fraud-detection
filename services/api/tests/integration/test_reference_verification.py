from __future__ import annotations

import io
import os
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from flask import Flask
from sqlalchemy import select

from momo_fdvs.extensions import db
from momo_fdvs.models import (
    AnalysisRun,
    FraudRuleSet,
    OCRConfirmation,
    OCRResult,
    Receipt,
    Role,
    Transaction,
    User,
    UserRole,
    VerificationResult,
)
from momo_fdvs.security.passwords import hash_password

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="requires an isolated PostgreSQL test database",
)

TEST_CREDENTIAL = "Correct-Horse-Battery-7"
HEADER = (
    "provider_code,transaction_reference,amount,currency,sender_name,sender_phone,"
    "receiver_name,receiver_phone,occurred_at,transaction_status,source_system_id\n"
)


@pytest.fixture(autouse=True)
def roles(app: Flask) -> None:
    with app.app_context():
        for code in ("USER", "ADMIN", "INVESTIGATOR"):
            if db.session.get(Role, code) is None:
                db.session.add(Role(code=code, description=f"Test {code}"))
        db.session.commit()


def _staff(app: Flask, role: str) -> str:
    email = f"{role.lower()}-{uuid.uuid4()}@example.test"
    with app.app_context():
        user = User(
            email=email,
            password_hash=hash_password(TEST_CREDENTIAL),
            full_name=f"Test {role.title()}",
            status="ACTIVE",
            password_changed_at=datetime.now(UTC),
        )
        db.session.add(user)
        db.session.flush()
        db.session.add(
            UserRole(
                user_id=user.id,
                role_code=role,
                granted_by=None,
                granted_at=datetime.now(UTC),
            )
        )
        db.session.commit()
    return email


def _login(client: Any, email: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": TEST_CREDENTIAL},
        headers={"X-Client-Type": "mobile"},
    )
    assert response.status_code == 200
    return response.json["data"]


def _register(client: Any) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Verification Owner",
            "email": f"owner-{uuid.uuid4()}@example.test",
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


def _csv(*, invalid: bool = False, reference: str = "ABC123456") -> bytes:
    source_id = uuid.uuid4()
    rows = (
        f"MTN_MOMO,{reference},125.00,GHS,Demo Sender,0240000002,Demo Receiver,"
        f"0240000001,2026-08-08T14:30:00Z,SUCCESSFUL,controlled-{source_id}\n"
    )
    if invalid:
        rows += "MTN_MOMO,BAD,not-money,GHS,,,,,,,controlled-bad\n"
    return (HEADER + rows).encode()


def _import(
    client: Any,
    session: dict[str, Any],
    *,
    invalid: bool = False,
    reference: str = "ABC123456",
) -> str:
    created = client.post(
        "/api/v1/admin/reference-imports",
        data={
            "source_label": f"controlled-{uuid.uuid4()}",
            "file": (
                io.BytesIO(_csv(invalid=invalid, reference=reference)),
                "references.csv",
                "text/csv",
            ),
        },
        headers=_headers(session, f"upload-{uuid.uuid4()}"),
        content_type="multipart/form-data",
    )
    assert created.status_code == 201, created.get_data(as_text=True)
    return str(created.json["data"]["id"])


def test_admin_import_lifecycle_invalid_report_and_staff_lookup(app: Flask) -> None:
    client = app.test_client()
    admin = _login(client, _staff(app, "ADMIN"))
    batch_id = _import(client, admin, invalid=True, reference="LIFECYCLE123")

    listed = client.get("/api/v1/admin/reference-imports", headers=_headers(admin))
    assert listed.status_code == 200
    assert listed.json["data"]["total"] >= 1
    assert "object_key" not in listed.get_data(as_text=True)

    validated = client.post(
        f"/api/v1/admin/reference-imports/{batch_id}/validate", headers=_headers(admin)
    )
    assert validated.status_code == 200
    assert validated.json["data"]["batch"]["valid_rows"] == 1
    assert validated.json["data"]["batch"]["invalid_rows"] == 1
    assert "INVALID_DECIMAL" in {error["code"] for error in validated.json["data"]["errors"]}

    report = client.get(
        f"/api/v1/admin/reference-imports/{batch_id}/invalid-rows",
        headers=_headers(admin),
    )
    assert report.status_code == 200
    assert report.headers["Cache-Control"].startswith("private, no-store")
    assert report.headers["X-Content-Type-Options"] == "nosniff"

    key = f"commit-{uuid.uuid4()}"
    committed = client.post(
        f"/api/v1/admin/reference-imports/{batch_id}/commit",
        headers=_headers(admin, key),
    )
    assert committed.status_code == 200
    assert committed.json["data"]["committed_rows"] == 1
    replay = client.post(
        f"/api/v1/admin/reference-imports/{batch_id}/commit",
        headers=_headers(admin, key),
    )
    assert replay.status_code == 200
    assert replay.json["data"]["replayed"] is True

    investigator = _login(client, _staff(app, "INVESTIGATOR"))
    references = client.get("/api/v1/admin/reference-transactions", headers=_headers(investigator))
    assert references.status_code == 200
    item = references.json["data"]["references"][0]
    assert item["transaction_reference_masked"] == "LIFE...23"
    detail = client.get(
        f"/api/v1/admin/reference-transactions/{item['id']}",
        headers=_headers(investigator),
    )
    assert detail.status_code == 200
    assert "raw_row" not in detail.get_data(as_text=True)

    user = _register(client)
    denied = client.get("/api/v1/admin/reference-imports", headers=_headers(user))
    assert denied.status_code == 403


def _ready_transaction(app: Flask, user_id: uuid.UUID, *, amount: str = "125.00") -> uuid.UUID:
    now = datetime.now(UTC)
    with app.app_context():
        transaction = Transaction(user_id=user_id, status="READY")
        db.session.add(transaction)
        db.session.flush()
        receipt = Receipt(
            transaction_id=transaction.id,
            object_key=f"receipts/{transaction.id}/controlled.png",
            original_filename="controlled.png",
            media_type="image/png",
            size_bytes=10,
            width_px=640,
            height_px=480,
            sha256="a" * 64,
            perceptual_hash="abcdef0123456789",
            quality_warnings=[],
            storage_version="local-v1",
        )
        db.session.add(receipt)
        db.session.flush()
        ocr = OCRResult(
            receipt_id=receipt.id,
            engine_name="tesseract",
            engine_version="controlled",
            pipeline_version="ocr-pipeline-v1",
            selected_variant="original",
            raw_text="controlled",
            token_data=[],
            extracted_fields={},
            field_confidences={},
            warnings=[],
        )
        db.session.add(ocr)
        db.session.flush()
        db.session.add(
            OCRConfirmation(
                ocr_result_id=ocr.id,
                transaction_id=transaction.id,
                confirmed_fields={
                    "provider_code": "MTN_MOMO",
                    "transaction_reference": "ABC123456",
                    "amount": amount,
                    "currency": "GHS",
                    "sender_name": "Demo Sender",
                    "sender_phone": "+233240000002",
                    "receiver_name": "Demo Receiver",
                    "receiver_phone": "+233240000001",
                    "occurred_at": "2026-08-08T14:30:00Z",
                    "status_text": "SUCCESSFUL",
                },
                corrections=[],
                confirmed_by=user_id,
                confirmed_at=now,
                schema_version="ocr-fields-v1",
            )
        )
        if db.session.scalar(select(FraudRuleSet).where(FraudRuleSet.status == "ACTIVE")) is None:
            db.session.add(
                FraudRuleSet(
                    version=f"controlled-{uuid.uuid4()}",
                    status="ACTIVE",
                    risk_weights={},
                    thresholds={},
                    description="Controlled active configuration; no model inference.",
                    created_by=user_id,
                    activated_by=user_id,
                    activated_at=now,
                    row_version=1,
                )
            )
        db.session.commit()
        return transaction.id


def test_analysis_persists_verification_separately_from_unavailable_risk(app: Flask) -> None:
    client = app.test_client()
    admin = _login(client, _staff(app, "ADMIN"))
    batch_id = _import(client, admin)
    assert (
        client.post(
            f"/api/v1/admin/reference-imports/{batch_id}/validate", headers=_headers(admin)
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/admin/reference-imports/{batch_id}/commit",
            headers=_headers(admin, f"commit-{uuid.uuid4()}"),
        ).status_code
        == 200
    )
    owner = _register(client)
    owner_id = uuid.UUID(owner["user"]["id"])
    transaction_id = _ready_transaction(app, owner_id)
    key = f"analysis-{uuid.uuid4()}"

    response = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses",
        headers=_headers(owner, key),
    )
    assert response.status_code == 202, response.get_data(as_text=True)
    data = response.json["data"]
    assert data["status"] == "PARTIAL"
    assert data["verification"]["status"] == "VERIFIED"
    assert data["verification"]["basis"] == "STORED_IMPORTED_RECORD"
    assert "not live confirmation" in data["verification"]["disclaimer"]
    assert data["risk"] == {
        "class": None,
        "reason_code": "MODEL_AND_RISK_STAGES_NOT_AVAILABLE",
        "score": None,
        "status": "UNAVAILABLE",
        "summary": "Fraud risk has not been calculated in this build.",
    }

    replay = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses",
        headers=_headers(owner, key),
    )
    assert replay.status_code == 202
    assert replay.json["data"]["replayed"] is True
    assert replay.json["data"]["analysis_id"] == data["analysis_id"]

    with app.app_context():
        run = db.session.get(AnalysisRun, uuid.UUID(data["analysis_id"]))
        assert run is not None
        assert run.risk_score is None and run.risk_class is None
        result = db.session.scalar(
            select(VerificationResult).where(VerificationResult.analysis_run_id == run.id)
        )
        assert result is not None and result.status == "VERIFIED"
        assert result.verifier_version == "stored-reference-verifier-v1"

    mismatch_transaction_id = _ready_transaction(app, owner_id, amount="999.00")
    mismatch = client.post(
        f"/api/v1/transactions/{mismatch_transaction_id}/analyses",
        headers=_headers(owner, f"analysis-{uuid.uuid4()}"),
    )
    assert mismatch.status_code == 202
    assert mismatch.json["data"]["verification"]["status"] == "MISMATCH"
    amount_comparison = mismatch.json["data"]["verification"]["field_comparisons"]["amount"]
    assert amount_comparison["reason"] == "FIELD_DIFFERED"
    assert mismatch.json["data"]["risk"]["status"] == "UNAVAILABLE"
