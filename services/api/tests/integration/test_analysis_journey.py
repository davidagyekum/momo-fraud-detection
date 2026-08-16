from __future__ import annotations

import io
import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from flask import Flask
from PIL import Image
from sqlalchemy import select

from momo_fdvs.extensions import db
from momo_fdvs.models import (
    FraudRuleSet,
    ReferenceImportBatch,
    ReferenceTransaction,
    Role,
    User,
    UserRole,
)
from momo_fdvs.security.passwords import hash_password
from momo_fdvs.services.ocr import OCRPipelineResult, parse_fields

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="requires an isolated PostgreSQL test database",
)

TEST_CREDENTIAL = "Correct-Horse-Battery-7"
TEXT = """MTN MOMO
TRANSACTION ID: JOURNEY12345
AMOUNT: GHS 25.00
SENDER NAME: Demo Sender
SENDER PHONE: 0240000002
RECEIVER NAME: Demo Receiver
RECEIVER PHONE: 0240000001
DATE/TIME: 2026-08-15 12:30
STATUS: Successful"""


@pytest.fixture(autouse=True)
def roles(app: Flask) -> None:
    with app.app_context():
        for code in ("USER", "ADMIN", "INVESTIGATOR"):
            if db.session.get(Role, code) is None:
                db.session.add(Role(code=code, description=f"Test {code}"))
        db.session.commit()


def _headers(session: dict[str, Any], key: str | None = None) -> dict[str, str]:
    result = {"Authorization": f"Bearer {session['access_token']}"}
    if key:
        result["Idempotency-Key"] = key
    return result


def _png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (900, 1200), "white").save(output, format="PNG")
    return output.getvalue()


def _pipeline(app: Flask, reference: str) -> OCRPipelineResult:
    text = TEXT.replace("JOURNEY12345", reference)
    tokens = [
        {
            "id": index,
            "text": word,
            "confidence": 96.0,
            "x": index * 12,
            "y": 10,
            "width": 10,
            "height": 12,
            "line_id": "1:1:1:1",
        }
        for index, word in enumerate(text.replace("\n", " ").split())
    ]
    with app.app_context():
        fields, provider = parse_fields(text, tokens, 0.75)
    return OCRPipelineResult(
        engine_version="controlled-journey",
        selected_variant="GRAY_CLAHE",
        selected_image=_png(),
        raw_text=text,
        tokens=tokens,
        fields=fields,
        provider=provider,
        warnings=[],
        candidate_summary=[
            {
                "variant": "GRAY_CLAHE",
                "psm": 6,
                "score": 0.98,
                "required_field_coverage": 1.0,
            }
        ],
        quality_features={"laplacian_variance": 100.0},
        partial=False,
    )


def _confirmed_fields(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider_code": run["provider"]["value"],
        **{name: value["value"] for name, value in run["fields"].items()},
    }


def _seed_reference(app: Flask, owner_id: uuid.UUID, fields: dict[str, Any]) -> None:
    marker = uuid.uuid4().hex
    now = datetime.now(UTC)
    with app.app_context():
        owner = db.session.get(User, owner_id)
        assert owner is not None
        active = db.session.scalar(select(FraudRuleSet).where(FraudRuleSet.status == "ACTIVE"))
        if active is None:
            db.session.add(
                FraudRuleSet(
                    version=f"journey-{marker}",
                    status="ACTIVE",
                    risk_weights={},
                    thresholds={},
                    description="Controlled PR18 journey rule set.",
                    created_by=owner.id,
                    activated_by=owner.id,
                    activated_at=now,
                    row_version=1,
                )
            )
        batch = ReferenceImportBatch(
            source_label=f"controlled-journey-{marker}",
            original_filename="controlled-journey.csv",
            file_sha256=marker * 2,
            status="COMMITTED",
            total_rows=1,
            valid_rows=1,
            invalid_rows=0,
            uploaded_by=owner.id,
            committed_at=now,
        )
        db.session.add(batch)
        db.session.flush()
        db.session.add(
            ReferenceTransaction(
                import_batch_id=batch.id,
                provider_code=fields["provider_code"],
                transaction_reference=fields["transaction_reference"],
                amount=Decimal(fields["amount"]),
                currency=fields["currency"],
                sender_name_normalised="DEMO SENDER",
                sender_phone_e164="+233240000002",
                receiver_name_normalised="DEMO RECEIVER",
                receiver_phone_e164="+233240000001",
                occurred_at=datetime(2026, 8, 15, 12, 30, tzinfo=UTC),
                transaction_status="SUCCESSFUL",
                raw_row={"controlled_fixture": True},
            )
        )
        db.session.commit()


def _staff_session(app: Flask, client: Any, role: str) -> dict[str, Any]:
    email = f"journey-{role.lower()}-{uuid.uuid4()}@example.test"
    with app.app_context():
        user = User(
            email=email,
            password_hash=hash_password(TEST_CREDENTIAL),
            full_name=f"Journey {role.title()}",
            status="ACTIVE",
            password_changed_at=datetime.now(UTC),
        )
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_code=role, granted_at=datetime.now(UTC)))
        db.session.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": TEST_CREDENTIAL},
        headers={"X-Client-Type": "mobile"},
    )
    assert login.status_code == 200
    return login.json["data"]


def test_controlled_screenshot_analysis_journey(
    app: Flask, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    client = app.test_client()
    email = f"journey-{uuid.uuid4()}@example.test"
    registered = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Journey Owner", "email": email, "password": TEST_CREDENTIAL},
        headers={"X-Client-Type": "mobile"},
    )
    assert registered.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": TEST_CREDENTIAL},
        headers={"X-Client-Type": "mobile"},
    )
    assert login.status_code == 200
    session = login.json["data"]

    upload = client.post(
        "/api/v1/transactions",
        data={
            "receipt": (io.BytesIO(_png()), "controlled-journey.png", "image/png"),
            "source": "GALLERY",
        },
        headers=_headers(session, f"upload-{uuid.uuid4()}"),
        content_type="multipart/form-data",
    )
    assert upload.status_code == 201, upload.get_data(as_text=True)
    transaction_id = upload.json["data"]["transaction"]["id"]

    reference = f"J{uuid.uuid4().hex[:12].upper()}"
    monkeypatch.setattr(
        "momo_fdvs.services.ocr.execute_ocr", lambda *_args: _pipeline(app, reference)
    )
    ocr = client.post(
        f"/api/v1/transactions/{transaction_id}/ocr",
        headers=_headers(session, f"ocr-{uuid.uuid4()}"),
    )
    assert ocr.status_code == 200, ocr.get_data(as_text=True)
    run = ocr.json["data"]
    fields = _confirmed_fields(run)
    confirmation = client.post(
        f"/api/v1/transactions/{transaction_id}/ocr-confirmations",
        json={"ocr_result_id": run["ocr_result_id"], "fields": fields},
        headers=_headers(session, f"confirm-{uuid.uuid4()}"),
    )
    assert confirmation.status_code == 201, confirmation.get_data(as_text=True)
    _seed_reference(app, uuid.UUID(session["user"]["id"]), fields)

    started = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses",
        headers=_headers(session, f"analysis-{uuid.uuid4()}"),
    )
    assert started.status_code == 202, started.get_data(as_text=True)
    analysis_id = started.json["data"]["analysis_run_id"]
    result = client.get(f"/api/v1/analyses/{analysis_id}", headers=_headers(session))
    history = client.get("/api/v1/transactions", headers=_headers(session))
    detail = client.get(f"/api/v1/transactions/{transaction_id}", headers=_headers(session))
    evidence = client.get(f"/api/v1/analyses/{analysis_id}/evidence", headers=_headers(session))
    assert all(response.status_code == 200 for response in (result, history, detail, evidence))
    assert result.json["data"]["id"] == analysis_id
    assert history.json["data"]["items"][0]["latest_analysis"]["id"] == analysis_id
    assert detail.json["data"]["latest_analysis"]["id"] == analysis_id
    assert evidence.json["data"]["analysis_run_id"] == analysis_id
    assert result.json["data"]["risk"]["band"] == "inconclusive"
    assert result.json["data"]["verification"]["status"] == "VERIFIED"
    assert result.json["data"]["evidence_summary"]["image_model"]["status"] == "UNAVAILABLE"
    public_text = " ".join(
        response.get_data(as_text=True) for response in (result, history, detail, evidence)
    )
    assert "controlled-journey.png" not in public_text
    assert "LOCAL_PRIVATE_STORAGE_ROOT" not in public_text
    assert "object_key" not in public_text
    assert "locked_test" not in public_text
    assert "controlled-journey.png" not in caplog.text

    report = client.post(
        f"/api/v1/transactions/{transaction_id}/reports",
        json={"format": "HTML"},
        headers=_headers(session, f"report-{uuid.uuid4()}"),
    )
    assert report.status_code == 201
    report_download = client.get(report.json["data"]["download_url"], headers=_headers(session))
    assert report_download.status_code == 200
    assert report_download.headers["Cache-Control"].startswith("private, no-store")
    report_text = report_download.get_data(as_text=True)
    assert "controlled-journey.png" not in report_text
    assert reference not in report_text

    opened = client.post(
        f"/api/v1/transactions/{transaction_id}/fraud-reports",
        json={
            "category": "OTHER",
            "description": "Controlled acceptance review request.",
        },
        headers=_headers(session, f"case-{uuid.uuid4()}"),
    )
    assert opened.status_code == 201
    case_id = opened.json["data"]["id"]

    investigator = _staff_session(app, client, "INVESTIGATOR")
    admin = _staff_session(app, client, "ADMIN")
    queue = client.get("/api/v1/admin/cases?status=OPEN", headers=_headers(investigator))
    assert queue.status_code == 200
    assert any(item["id"] == case_id for item in queue.json["data"]["items"])
    investigator_id = investigator["user"]["id"]
    assigned = client.post(
        f"/api/v1/admin/cases/{case_id}/assign",
        json={"investigator_id": investigator_id, "expected_case_version": 1},
        headers=_headers(admin),
    )
    assert assigned.status_code == 200
    review = client.post(
        f"/api/v1/admin/cases/{case_id}/start-review",
        json={"expected_case_version": 2},
        headers=_headers(investigator),
    )
    assert review.status_code == 200
    note = client.post(
        f"/api/v1/admin/cases/{case_id}/notes",
        json={"note": "Controlled evidence reviewed.", "expected_case_version": 3},
        headers=_headers(investigator),
    )
    assert note.status_code == 200
    decision = client.post(
        f"/api/v1/admin/cases/{case_id}/decisions",
        json={
            "outcome": "DISMISSED",
            "reason": "Controlled screenshot and stored reference agree.",
            "expected_case_version": 4,
        },
        headers=_headers(investigator),
    )
    assert decision.status_code == 200
    assert decision.json["data"]["status"] == "DECIDED"

    owner_case = client.get(f"/api/v1/fraud-reports/{case_id}", headers=_headers(session))
    notifications = client.get("/api/v1/notifications", headers=_headers(session))
    assert owner_case.status_code == 200
    assert owner_case.json["data"]["status"] == "DECIDED"
    assert notifications.status_code == 200
    assert notifications.json["data"]["total"] >= 2

    for path in (
        "/api/v1/admin/dashboard",
        "/api/v1/admin/audit-logs",
        "/api/v1/admin/system-status",
        "/api/v1/admin/models",
        "/api/v1/admin/rule-sets",
    ):
        response = client.get(path, headers=_headers(admin))
        assert response.status_code == 200, response.get_data(as_text=True)
