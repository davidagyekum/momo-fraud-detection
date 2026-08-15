from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
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
    VerificationResult,
)

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


def _register(client: Any, name: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": name,
            "email": f"history-{uuid.uuid4()}@example.test",
            "password": TEST_CREDENTIAL,
        },
        headers={"X-Client-Type": "mobile"},
    )
    assert response.status_code == 201
    return response.json["data"]


def _headers(session: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


def _active_rule_set(owner: User, now: datetime) -> FraudRuleSet:
    rule_set = db.session.scalar(select(FraudRuleSet).where(FraudRuleSet.status == "ACTIVE"))
    if rule_set is not None:
        return rule_set
    rule_set = FraudRuleSet(
        version=f"history-{uuid.uuid4().hex}",
        status="ACTIVE",
        risk_weights={},
        thresholds={},
        description="Controlled history fixture.",
        created_by=owner.id,
        activated_by=owner.id,
        activated_at=now,
        row_version=1,
    )
    db.session.add(rule_set)
    db.session.flush()
    return rule_set


def _seed_history(
    app: Flask, owner_id: uuid.UUID, other_owner_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    now = datetime.now(UTC)
    with app.app_context():
        owner = db.session.get(User, owner_id)
        assert owner is not None
        rule_set = _active_rule_set(owner, now)
        transaction = Transaction(
            user_id=owner_id,
            status="PARTIAL",
            provider_code="MTN_MOMO",
            display_reference_masked="HIST...42",
            created_at=now - timedelta(hours=1),
        )
        newer = Transaction(
            user_id=owner_id,
            status="READY",
            provider_code="TELECEL_CASH",
            display_reference_masked="NEW...88",
            created_at=now,
        )
        other = Transaction(
            user_id=other_owner_id,
            status="PARTIAL",
            provider_code="MTN_MOMO",
            display_reference_masked="OTHER...99",
            created_at=now + timedelta(minutes=1),
        )
        db.session.add_all([transaction, newer, other])
        db.session.flush()
        receipt = Receipt(
            transaction_id=transaction.id,
            object_key=f"private/{owner_id}/{transaction.id}/secret.png",
            original_filename="private-history.png",
            media_type="image/png",
            size_bytes=128,
            width_px=96,
            height_px=160,
            sha256=uuid.uuid4().hex * 2,
            perceptual_hash="0123456789abcdef",
            quality_score=Decimal("0.9000"),
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
            raw_text="PRIVATE RAW OCR MUST NOT LEAK",
            token_data=[],
            extracted_fields={},
            field_confidences={},
            warnings=[],
            required_field_accuracy_hint=Decimal("0.95"),
        )
        db.session.add(ocr)
        db.session.flush()
        confirmation = OCRConfirmation(
            ocr_result_id=ocr.id,
            transaction_id=transaction.id,
            confirmed_fields={
                "amount": "125.00",
                "transaction_reference": "PRIVATE-CONFIRMED-VALUE",
            },
            corrections=[{"field": "amount", "reason": "Controlled correction."}],
            confirmed_by=owner_id,
            confirmed_at=now,
            schema_version="ocr-fields-v1",
        )
        db.session.add(confirmation)
        db.session.flush()
        policy = {
            "status": "PARTIAL",
            "band": "inconclusive",
            "legacy_risk_class": None,
            "score": None,
            "summary": "The available evidence is insufficient for a fraud-risk conclusion.",
            "reasons": [],
            "missing_signals": ["IMAGE_MODEL_NOT_ACTIVE"],
            "limitations": ["No active image model was available."],
            "policy_version": "risk-policy-history-v1",
        }
        runs: list[AnalysisRun] = []
        for index, completed_at in enumerate(
            (now - timedelta(minutes=20), now - timedelta(minutes=10)), start=1
        ):
            run = AnalysisRun(
                transaction_id=transaction.id,
                ocr_confirmation_id=confirmation.id,
                status="PARTIAL",
                current_stage="FINALIZE",
                rule_set_id=rule_set.id,
                idempotency_key_hash=str(index) * 64,
                request_fingerprint=str(index + 1) * 64,
                attempt_count=1,
                queued_at=completed_at - timedelta(seconds=2),
                started_at=completed_at - timedelta(seconds=1),
                completed_at=completed_at,
                component_scores={"policy": policy},
                top_reasons=[],
                configuration_snapshot={
                    "policy_version": "risk-policy-history-v1",
                    "policy_sha256": "a" * 64,
                    "rule_set_version": rule_set.version,
                    "ocr_pipeline_version": "ocr-pipeline-v1",
                    "ocr_engine_version": "controlled",
                    "image_forensics_version": "forensics-v1",
                    "image_model_version": None,
                    "structured_model_version": None,
                },
            )
            db.session.add(run)
            db.session.flush()
            runs.append(run)
        db.session.add(
            VerificationResult(
                analysis_run_id=runs[-1].id,
                reference_transaction_id=None,
                status="UNVERIFIED",
                verifier_version="stored-reference-verifier-v1",
                candidate_method="NONE",
                field_comparisons={},
                matched_field_count=0,
                mismatched_field_count=0,
                warnings=["REFERENCE_NOT_FOUND"],
            )
        )
        transaction.latest_analysis_run_id = runs[-1].id
        db.session.commit()
        return transaction.id, newer.id, other.id


def test_owner_history_filters_pagination_and_detail(app: Flask) -> None:
    client = app.test_client()
    owner = _register(client, "History Owner")
    other_owner = _register(client, "Other History Owner")
    transaction_id, newer_id, other_id = _seed_history(
        app,
        uuid.UUID(owner["user"]["id"]),
        uuid.UUID(other_owner["user"]["id"]),
    )

    history = client.get("/api/v1/transactions?page=1&page_size=20", headers=_headers(owner))
    assert history.status_code == 200
    items = history.json["data"]["items"]
    assert [item["id"] for item in items[:2]] == [str(newer_id), str(transaction_id)]
    assert all(item["owner_visible"] for item in items)
    assert str(other_id) not in {item["id"] for item in items}

    filtered = client.get(
        "/api/v1/transactions?page=1&page_size=20&band=inconclusive"
        "&provider=MTN_MOMO&status=PARTIAL&verification=UNVERIFIED",
        headers=_headers(owner),
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json["data"]["items"]] == [str(transaction_id)]

    invalid = client.get("/api/v1/transactions?page_size=101", headers=_headers(owner))
    assert invalid.status_code == 422

    detail = client.get(f"/api/v1/transactions/{transaction_id}", headers=_headers(owner))
    assert detail.status_code == 200
    data = detail.json["data"]
    assert data["latest_analysis"]["id"] == data["analysis_runs"][0]["id"]
    assert len(data["analysis_runs"]) == 2
    assert data["confirmed_field_coverage"] == {
        "field_count": 2,
        "correction_count": 1,
        "schema_version": "ocr-fields-v1",
    }
    body = detail.get_data(as_text=True)
    assert "PRIVATE RAW OCR" not in body
    assert "PRIVATE-CONFIRMED-VALUE" not in body
    assert "private/" not in body

    denied = client.get(f"/api/v1/transactions/{transaction_id}", headers=_headers(other_owner))
    assert denied.status_code == 404
