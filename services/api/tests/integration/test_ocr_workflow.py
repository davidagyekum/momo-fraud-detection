from __future__ import annotations

import io
import os
import uuid
from typing import Any

import pytest
from flask import Flask
from PIL import Image
from sqlalchemy import func, select

from momo_fdvs.extensions import db
from momo_fdvs.models import (
    AuditLog,
    OCRConfirmation,
    OCRResult,
    ReceiptDerivative,
    Role,
)
from momo_fdvs.services.ocr import OCRFailure, OCRPipelineResult, parse_fields

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="requires an isolated PostgreSQL test database",
)

TEST_CREDENTIAL = "Correct-Horse-Battery-7"
CONTROLLED_TEXT = """MTN MOMO
TRANSACTION ID: ABC123456
AMOUNT: GHS 125.00
SENDER NAME: Demo Sender
SENDER PHONE: 0240000002
RECEIVER NAME: Demo Receiver
RECEIVER PHONE: 0240000001
DATE/TIME: 2026-08-08 14:30
STATUS: Successful"""


@pytest.fixture(autouse=True)
def roles(app: Flask) -> None:
    with app.app_context():
        for code in ("USER", "ADMIN", "INVESTIGATOR"):
            if db.session.get(Role, code) is None:
                db.session.add(Role(code=code, description=f"Test {code}"))
        db.session.commit()


def _png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (900, 1200), "white").save(output, format="PNG")
    return output.getvalue()


def _register(client: Any) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "OCR Owner",
            "email": f"ocr-{uuid.uuid4()}@example.test",
            "password": TEST_CREDENTIAL,
        },
        headers={"X-Client-Type": "mobile"},
    )
    assert response.status_code == 201
    return response.json["data"]


def _headers(session: dict[str, Any], key: str | None = None) -> dict[str, str]:
    result = {"Authorization": f"Bearer {session['access_token']}"}
    if key:
        result["Idempotency-Key"] = key
    return result


def _upload(client: Any, session: dict[str, Any]) -> str:
    response = client.post(
        "/api/v1/transactions",
        data={
            "receipt": (io.BytesIO(_png()), "receipt.png", "image/png"),
            "source": "GALLERY",
        },
        headers=_headers(session, f"upload-{uuid.uuid4()}"),
        content_type="multipart/form-data",
    )
    assert response.status_code == 201, response.get_data(as_text=True)
    return str(response.json["data"]["transaction"]["id"])


def _tokens() -> list[dict[str, Any]]:
    return [
        {
            "id": index,
            "text": word,
            "confidence": 94.0,
            "x": index * 12,
            "y": 10,
            "width": 10,
            "height": 12,
            "line_id": "1:1:1:1",
        }
        for index, word in enumerate(CONTROLLED_TEXT.replace("\n", " ").split())
    ]


def _pipeline(
    app: Flask,
    *,
    partial: bool = False,
    raw_text: str = CONTROLLED_TEXT,
) -> OCRPipelineResult:
    with app.app_context():
        fields, provider = parse_fields(raw_text, _tokens(), 0.75)
    output = io.BytesIO()
    Image.new("L", (900, 1200), "white").save(output, format="PNG")
    warnings = ["OCR_ENGINE_UNAVAILABLE"] if partial else []
    return OCRPipelineResult(
        engine_version="unavailable" if partial else "5.3.0",
        selected_variant="GRAY_CLAHE",
        selected_image=output.getvalue(),
        raw_text="" if partial else raw_text,
        tokens=[] if partial else _tokens(),
        fields=fields,
        provider=provider,
        warnings=warnings,
        candidate_summary=[
            {
                "variant": "GRAY_CLAHE",
                "psm": 6,
                "score": 0.95,
                "required_field_coverage": 1.0,
            }
        ],
        quality_features={"laplacian_variance": 100.0},
        partial=partial,
    )


def _confirmed_fields(run_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider_code": run_data["provider"]["value"],
        "transaction_reference": run_data["fields"]["transaction_reference"]["value"],
        "amount": run_data["fields"]["amount"]["value"],
        "currency": run_data["fields"]["currency"]["value"],
        "sender_name": run_data["fields"]["sender_name"]["value"],
        "sender_phone": run_data["fields"]["sender_phone"]["value"],
        "receiver_name": run_data["fields"]["receiver_name"]["value"],
        "receiver_phone": run_data["fields"]["receiver_phone"]["value"],
        "occurred_at": run_data["fields"]["occurred_at"]["value"],
        "status_text": run_data["fields"]["status_text"]["value"],
    }


def test_ocr_run_replay_review_and_owner_isolation(
    app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = app.test_client()
    owner = _register(client)
    transaction_id = _upload(client, owner)
    pipeline = _pipeline(app)
    monkeypatch.setattr("momo_fdvs.services.ocr.execute_ocr", lambda *_args: pipeline)

    key = f"ocr-run-{uuid.uuid4()}"
    created = client.post(
        f"/api/v1/transactions/{transaction_id}/ocr", headers=_headers(owner, key)
    )
    assert created.status_code == 200, created.get_data(as_text=True)
    data = created.json["data"]
    assert data["status"] == "OCR_READY"
    assert data["provider"]["value"] == "MTN_MOMO"
    assert data["fields"]["amount"]["value"] == "125.00"
    assert data["selected_variant"] == "GRAY_CLAHE"
    assert data["fraud_preview"]["score_is_probability"] is False
    assert data["fraud_preview"]["class"] is None
    assert "token_data" not in created.get_data(as_text=True)

    replay = client.post(f"/api/v1/transactions/{transaction_id}/ocr", headers=_headers(owner, key))
    assert replay.status_code == 200
    assert replay.json["data"]["replayed"] is True
    assert replay.json["data"]["ocr_result_id"] == data["ocr_result_id"]

    review = client.get(
        f"/api/v1/transactions/{transaction_id}/ocr-review", headers=_headers(owner)
    )
    assert review.status_code == 200
    assert review.json["data"]["raw_text"] == CONTROLLED_TEXT

    outsider = _register(client)
    denied = client.get(
        f"/api/v1/transactions/{transaction_id}/ocr-review", headers=_headers(outsider)
    )
    assert denied.status_code == 404

    with app.app_context():
        receipt_scope = OCRResult.receipt.has(transaction_id=uuid.UUID(transaction_id))
        assert (
            db.session.scalar(select(func.count()).select_from(OCRResult).where(receipt_scope)) == 1
        )
        derivative = db.session.scalar(
            select(ReceiptDerivative).where(
                ReceiptDerivative.kind == "OCR_VARIANT",
                ReceiptDerivative.receipt.has(transaction_id=uuid.UUID(transaction_id)),
            )
        )
        assert derivative is not None
        assert derivative.metadata_json["pipeline_version"] == "ocr-pipeline-v1"
        result = db.session.get(OCRResult, uuid.UUID(data["ocr_result_id"]))
        assert result is not None
        assert result.extracted_fields["_evidence"]["parser_version"] == "generic-parser-v1"
        assert result.extracted_fields["_text_fraud"]["ruleset_version"]


def test_ocr_review_returns_persisted_obvious_fraud_preview_without_private_matches(
    app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = app.test_client()
    owner = _register(client)
    transaction_id = _upload(client, owner)
    private_phone = "0244000000"
    scam_text = (
        f"{CONTROLLED_TEXT}\nYour MoMo wallet is blocked. "
        f"Send your PIN and OTP to {private_phone} immediately."
    )
    monkeypatch.setattr(
        "momo_fdvs.services.ocr.execute_ocr",
        lambda *_args: _pipeline(app, raw_text=scam_text),
    )

    response = client.post(
        f"/api/v1/transactions/{transaction_id}/ocr",
        headers=_headers(owner, f"ocr-fraud-{uuid.uuid4()}"),
    )

    assert response.status_code == 200
    preview = response.json["data"]["fraud_preview"]
    assert preview["class"] == "FRAUDULENT"
    assert preview["score_is_probability"] is False
    assert "PIN_OR_OTP_REQUEST" in preview["reason_codes"]
    assert private_phone not in str(preview)

    replay = client.get(
        f"/api/v1/transactions/{transaction_id}/ocr-review",
        headers=_headers(owner),
    )
    assert replay.json["data"]["fraud_preview"] == preview


def test_new_key_creates_immutable_ocr_result_but_reuses_derivative(
    app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = app.test_client()
    owner = _register(client)
    transaction_id = _upload(client, owner)
    pipeline = _pipeline(app)
    monkeypatch.setattr("momo_fdvs.services.ocr.execute_ocr", lambda *_args: pipeline)
    first = client.post(
        f"/api/v1/transactions/{transaction_id}/ocr",
        headers=_headers(owner, f"ocr-{uuid.uuid4()}"),
    )
    second = client.post(
        f"/api/v1/transactions/{transaction_id}/ocr",
        headers=_headers(owner, f"ocr-{uuid.uuid4()}"),
    )
    assert first.status_code == second.status_code == 200
    assert first.json["data"]["ocr_result_id"] != second.json["data"]["ocr_result_id"]
    with app.app_context():
        receipt_scope = OCRResult.receipt.has(transaction_id=uuid.UUID(transaction_id))
        assert (
            db.session.scalar(select(func.count()).select_from(OCRResult).where(receipt_scope)) == 2
        )
        derivative_scope = ReceiptDerivative.receipt.has(transaction_id=uuid.UUID(transaction_id))
        assert (
            db.session.scalar(
                select(func.count()).select_from(ReceiptDerivative).where(derivative_scope)
            )
            == 2
        )


def test_confirmation_preserves_original_and_enforces_analysis_guard(
    app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = app.test_client()
    owner = _register(client)
    transaction_id = _upload(client, owner)
    pipeline = _pipeline(app)
    monkeypatch.setattr("momo_fdvs.services.ocr.execute_ocr", lambda *_args: pipeline)
    run = client.post(
        f"/api/v1/transactions/{transaction_id}/ocr",
        headers=_headers(owner, f"ocr-{uuid.uuid4()}"),
    ).json["data"]

    blocked = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses", headers=_headers(owner)
    )
    assert blocked.status_code == 409
    assert blocked.json["error"]["code"] == "OCR_REVIEW_REQUIRED"

    fields = _confirmed_fields(run)
    fields["amount"] = "130.00"
    invalid = client.post(
        f"/api/v1/transactions/{transaction_id}/ocr-confirmations",
        json={"ocr_result_id": run["ocr_result_id"], "fields": fields},
        headers=_headers(owner, f"confirm-{uuid.uuid4()}"),
    )
    assert invalid.status_code == 422
    assert "amount" in invalid.json["error"]["field_errors"]

    key = f"confirm-{uuid.uuid4()}"
    payload = {
        "ocr_result_id": run["ocr_result_id"],
        "fields": fields,
        "correction_reasons": {"amount": "Checked against the private receipt image."},
    }
    confirmed = client.post(
        f"/api/v1/transactions/{transaction_id}/ocr-confirmations",
        json=payload,
        headers=_headers(owner, key),
    )
    assert confirmed.status_code == 201, confirmed.get_data(as_text=True)
    assert confirmed.json["data"]["status"] == "OCR_REVIEWED"
    assert confirmed.json["data"]["corrected_fields"] == ["amount"]

    replay = client.post(
        f"/api/v1/transactions/{transaction_id}/ocr-confirmations",
        json=payload,
        headers=_headers(owner, key),
    )
    assert replay.status_code == 200
    assert replay.json["data"]["replayed"] is True

    partial = client.post(
        f"/api/v1/transactions/{transaction_id}/analyses",
        headers=_headers(owner, f"analysis-{uuid.uuid4()}"),
    )
    assert partial.status_code == 202
    assert partial.json["data"]["status"] == "PARTIAL"
    analysis = client.get(partial.json["data"]["poll_url"], headers=_headers(owner))
    assert analysis.status_code == 200
    assert analysis.json["data"]["verification"]["status"] == "UNVERIFIED"
    assert analysis.json["data"]["risk"]["band"] == "inconclusive"

    with app.app_context():
        result = db.session.get(OCRResult, uuid.UUID(run["ocr_result_id"]))
        assert result is not None
        assert result.extracted_fields["amount"]["value"] == "125.00"
        confirmation = db.session.scalar(
            select(OCRConfirmation).where(
                OCRConfirmation.transaction_id == uuid.UUID(transaction_id)
            )
        )
        assert confirmation is not None
        assert confirmation.confirmed_fields["amount"] == "130.00"
        assert confirmation.corrections[0]["original_value"] == "125.00"
        assert confirmation.corrections[0]["reason"]
        actions = set(db.session.scalars(select(AuditLog.action)).all())
        assert {"ocr.completed", "ocr.confirmed"} <= actions


def test_tesseract_unavailable_is_persisted_as_partial(
    app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = app.test_client()
    owner = _register(client)
    transaction_id = _upload(client, owner)
    pipeline = _pipeline(app, partial=True)
    monkeypatch.setattr("momo_fdvs.services.ocr.execute_ocr", lambda *_args: pipeline)
    response = client.post(
        f"/api/v1/transactions/{transaction_id}/ocr",
        headers=_headers(owner, f"ocr-{uuid.uuid4()}"),
    )
    assert response.status_code == 200
    assert response.json["data"]["status"] == "OCR_PARTIAL"
    assert "OCR_ENGINE_UNAVAILABLE" in response.json["data"]["warnings"]
    assert response.json["data"]["engine_version"] == "unavailable"


def test_integrity_failure_is_explicit_and_does_not_create_result(
    app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = app.test_client()
    owner = _register(client)
    transaction_id = _upload(client, owner)

    def reject(*_args: Any) -> OCRPipelineResult:
        raise OCRFailure(
            "OCR_RECEIPT_HASH_MISMATCH",
            "The stored receipt failed its evidence-integrity check.",
            409,
        )

    monkeypatch.setattr("momo_fdvs.services.ocr.execute_ocr", reject)
    response = client.post(
        f"/api/v1/transactions/{transaction_id}/ocr",
        headers=_headers(owner, f"ocr-{uuid.uuid4()}"),
    )
    assert response.status_code == 409
    assert response.json["error"]["code"] == "OCR_RECEIPT_HASH_MISMATCH"
    with app.app_context():
        receipt_scope = OCRResult.receipt.has(transaction_id=uuid.UUID(transaction_id))
        assert (
            db.session.scalar(select(func.count()).select_from(OCRResult).where(receipt_scope)) == 0
        )
