from __future__ import annotations

import io
import os
import uuid
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pytest
from flask import Flask
from PIL import Image
from sqlalchemy import select, update
from sqlalchemy.exc import DBAPIError

from momo_fdvs.extensions import db
from momo_fdvs.models import (
    AnalysisRun,
    AnalysisStageRun,
    AuditLog,
    FraudRuleSet,
    ImageAnalysis,
    OCRConfirmation,
    OCRResult,
    Receipt,
    ReceiptDerivative,
    Role,
    Transaction,
    User,
    UserRole,
)
from momo_fdvs.security.passwords import hash_password
from momo_fdvs.services.receipts import inspect_receipt
from momo_fdvs.storage.base import ObjectStorage

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


def _receipt_bytes() -> bytes:
    values = np.full((480, 640, 3), 244, dtype=np.uint8)
    values[40:440:28, 35:600] = 45
    rng = np.random.default_rng(20260810)
    values[260:430, 360:610] = rng.integers(0, 256, size=(170, 250, 3), dtype=np.uint8)
    output = io.BytesIO()
    Image.fromarray(values).save(output, format="PNG")
    return output.getvalue()


def _register(client: Any, label: str = "Forensics Owner") -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": label,
            "email": f"forensics-{uuid.uuid4()}@example.test",
            "password": TEST_CREDENTIAL,
        },
        headers={"X-Client-Type": "mobile"},
    )
    assert response.status_code == 201
    return response.json["data"]


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


def _headers(session: dict[str, Any], key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    if key:
        headers["Idempotency-Key"] = key
    return headers


def _ready_transaction(
    app: Flask, owner_id: uuid.UUID, *, store_original: bool = True
) -> tuple[uuid.UUID, bytes]:
    content = _receipt_bytes()
    now = datetime.now(UTC)
    object_key = f"receipts/{owner_id}/{uuid.uuid4()}/original/controlled.png"
    with app.app_context():
        inspected = inspect_receipt(content, "controlled.png")
        storage: ObjectStorage = app.extensions["object_storage"]
        if store_original:
            storage.put_bytes(
                object_key,
                content,
                "image/png",
                {"sha256": inspected.sha256, "evidence": "controlled-original"},
            )
        transaction = Transaction(user_id=owner_id, status="READY", provider_code="MTN_MOMO")
        db.session.add(transaction)
        db.session.flush()
        receipt = Receipt(
            transaction_id=transaction.id,
            object_key=object_key,
            original_filename="controlled.png",
            media_type="image/png",
            size_bytes=len(content),
            width_px=inspected.width_px,
            height_px=inspected.height_px,
            sha256=inspected.sha256,
            perceptual_hash=inspected.perceptual_hash,
            quality_score=inspected.quality_score,
            quality_warnings=inspected.quality_warnings,
            storage_version="local-v1",
        )
        db.session.add(receipt)
        db.session.flush()
        tokens = [
            {
                "id": 0,
                "text": "Amount",
                "confidence": 96,
                "x": 5,
                "y": 30,
                "width": 70,
                "height": 18,
                "line_id": "1",
            },
            {
                "id": 1,
                "text": "125.00",
                "confidence": 95,
                "x": 100,
                "y": 34,
                "width": 85,
                "height": 18,
                "line_id": "1",
            },
            {
                "id": 2,
                "text": "Reference",
                "confidence": 94,
                "x": 20,
                "y": 90,
                "width": 90,
                "height": 20,
                "line_id": "2",
            },
            {
                "id": 3,
                "text": "ABC123456",
                "confidence": 94,
                "x": 130,
                "y": 115,
                "width": 120,
                "height": 36,
                "line_id": "2",
            },
        ]
        ocr = OCRResult(
            receipt_id=receipt.id,
            engine_name="tesseract",
            engine_version="controlled",
            pipeline_version="ocr-pipeline-v1",
            selected_variant="GRAY_CLAHE",
            raw_text="Amount 125.00\nReference ABC123456",
            token_data=tokens,
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
                confirmed_by=owner_id,
                confirmed_at=now,
                schema_version="ocr-fields-v1",
            )
        )
        if db.session.scalar(select(FraudRuleSet).where(FraudRuleSet.status == "ACTIVE")) is None:
            db.session.add(
                FraudRuleSet(
                    version="demo-1",
                    status="ACTIVE",
                    risk_weights={},
                    thresholds={},
                    description="Controlled deterministic evidence configuration; no risk model.",
                    created_by=owner_id,
                    activated_by=owner_id,
                    activated_at=now,
                    row_version=1,
                )
            )
        db.session.commit()
        return transaction.id, content


def test_image_evidence_persists_without_risk_and_diagnostics_are_private(app: Flask) -> None:
    client = app.test_client()
    owner = _register(client)
    owner_id = uuid.UUID(owner["user"]["id"])
    transaction_id, original = _ready_transaction(app, owner_id)
    response = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses",
        headers=_headers(owner, f"analysis-{uuid.uuid4()}"),
    )
    assert response.status_code == 202, response.get_data(as_text=True)
    started = response.json["data"]
    evidence_url = f"/api/v1/analyses/{started['analysis_run_id']}/evidence"
    owner_evidence = client.get(evidence_url, headers=_headers(owner))
    assert owner_evidence.status_code == 200
    data = owner_evidence.json["data"]
    assert data["image_evidence"]["status"] == "COMPLETED"
    assert data["image_evidence"]["classification"] is None
    assert data["image_evidence"]["tamper_probability"] is None
    assert data["image_evidence"]["policy"] == {
        "single_weak_signal_can_classify_fraud": False,
        "supporting_evidence_only": True,
    }
    assert "diagnostic_media" not in data["image_evidence"]
    deterministic_stage = next(
        stage for stage in data["stages"] if stage["stage"] == "DETERMINISTIC_IMAGE"
    )
    assert deterministic_stage["status"] == "COMPLETED"
    assert data["risk"]["band"] == "inconclusive"
    assert data["risk"]["class"] is None and data["risk"]["score"] is None

    assert "diagnostic_media" not in owner_evidence.json["data"]["image_evidence"]
    outsider = _register(client, "Forensics Outsider")
    assert client.get(evidence_url, headers=_headers(outsider)).status_code == 404
    assert (
        client.get(
            f"/api/v1/transactions/{transaction_id}/receipt?variant=ela",
            headers=_headers(owner),
        ).status_code
        == 403
    )

    investigator = _login(client, _staff(app, "INVESTIGATOR"))
    staff_evidence = client.get(evidence_url, headers=_headers(investigator))
    assert staff_evidence.status_code == 200
    media = staff_evidence.json["data"]["image_evidence"]["diagnostic_media"]
    assert media["access"] == "AUTHORISED_STAFF_ONLY"
    for variant in ("ela", "noise-map"):
        diagnostic = client.get(
            f"/api/v1/transactions/{transaction_id}/receipt?variant={variant}",
            headers=_headers(investigator),
        )
        assert diagnostic.status_code == 200
        assert diagnostic.content_type == "image/png"
        assert diagnostic.headers["Cache-Control"].startswith("private, no-store")

    analysis_id = uuid.UUID(started["analysis_run_id"])
    with app.app_context():
        run = db.session.get(AnalysisRun, analysis_id)
        result = db.session.scalar(
            select(ImageAnalysis).where(ImageAnalysis.analysis_run_id == analysis_id)
        )
        stage = db.session.scalar(
            select(AnalysisStageRun).where(
                AnalysisStageRun.analysis_run_id == analysis_id,
                AnalysisStageRun.stage == "DETERMINISTIC_IMAGE",
            )
        )
        transaction = db.session.get(Transaction, transaction_id)
        assert run is not None and run.risk_score is None and run.risk_class is None
        assert result is not None and result.image_tamper_probability is None
        assert result.engineered_features["weak_signal_policy"] == {
            "final_risk_class_emitted": False,
            "image_tamper_probability_emitted": False,
            "single_weak_signal_can_classify_fraud": False,
        }
        assert stage is not None and stage.status == "COMPLETED"
        assert transaction is not None and transaction.receipt is not None
        storage: ObjectStorage = app.extensions["object_storage"]
        assert storage.read_bytes(transaction.receipt.object_key) == original
        assert (
            len(
                db.session.scalars(
                    select(ReceiptDerivative).where(
                        ReceiptDerivative.receipt_id == transaction.receipt.id,
                        ReceiptDerivative.kind.in_(("ELA", "NOISE_MAP")),
                    )
                ).all()
            )
            == 2
        )
        actions = set(
            db.session.scalars(
                select(AuditLog.action).where(AuditLog.target_id.in_((analysis_id, transaction_id)))
            ).all()
        )
        assert {
            "analysis.evidence_viewed",
            "analysis.evidence_access_denied",
            "forensics.diagnostic_access_denied",
            "forensics.diagnostic_viewed",
        } <= actions

        with pytest.raises(DBAPIError):
            db.session.execute(
                update(ImageAnalysis)
                .where(ImageAnalysis.id == result.id)
                .values(algorithm_version="mutated")
            )
            db.session.commit()
        db.session.rollback()


def test_missing_private_original_returns_explicit_unavailable_image_state(app: Flask) -> None:
    client = app.test_client()
    owner = _register(client)
    owner_id = uuid.UUID(owner["user"]["id"])
    transaction_id, _ = _ready_transaction(app, owner_id, store_original=False)
    response = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses",
        headers=_headers(owner, f"analysis-{uuid.uuid4()}"),
    )
    assert response.status_code == 202
    evidence = client.get(
        f"/api/v1/analyses/{response.json['data']['analysis_run_id']}/evidence",
        headers=_headers(owner),
    )
    assert evidence.status_code == 200
    data = evidence.json["data"]
    assert data["verification"]["status"] in {
        "VERIFIED",
        "UNVERIFIED",
        "MISMATCH",
    }
    assert data["image_evidence"] == {
        "classification": None,
        "policy": {
            "single_weak_signal_can_classify_fraud": False,
            "supporting_evidence_only": True,
        },
        "reason_code": "IMAGE_STORAGE_UNAVAILABLE",
        "status": "UNAVAILABLE",
        "summary": "Deterministic image evidence was unavailable; no values were invented.",
        "tamper_probability": None,
    }
    deterministic_stage = next(
        stage for stage in data["stages"] if stage["stage"] == "DETERMINISTIC_IMAGE"
    )
    assert deterministic_stage["status"] == "FAILED"
    assert deterministic_stage["error_code"] == "IMAGE_STORAGE_UNAVAILABLE"
