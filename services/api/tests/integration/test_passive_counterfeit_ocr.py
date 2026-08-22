from __future__ import annotations

import io
import os
import shutil
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from flask import Flask
from tests.fixtures.generated_hybrid_negatives import (
    generated_body_phone_unknown_sender_png,
    generated_genuine_cash_in_one_typo_png,
    generated_genuine_cash_in_png,
    generated_genuine_payment_made_png,
    generated_numeric_sender_ordinary_chat_png,
    generated_official_advisory_png,
)
from tests.fixtures.generated_passive_counterfeit import (
    generated_passive_counterfeit_png,
)

from momo_fdvs.extensions import db
from momo_fdvs.models import Role

pytestmark = [
    pytest.mark.skipif(
        not os.getenv("TEST_DATABASE_URL"),
        reason="requires an isolated PostgreSQL test database",
    ),
    pytest.mark.skipif(
        shutil.which(os.getenv("TESSERACT_CMD", "tesseract")) is None,
        reason="requires a real Tesseract executable; covered by the Docker OCR gate",
    ),
]

TEST_CREDENTIAL = "Correct-Horse-Battery-7"


@pytest.fixture(autouse=True)
def roles(app: Flask) -> None:
    with app.app_context():
        for code in ("USER", "ADMIN", "INVESTIGATOR"):
            if db.session.get(Role, code) is None:
                db.session.add(Role(code=code, description=f"Test {code}"))
        db.session.commit()


def _register(client: Any) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Passive Counterfeit Test Owner",
            "email": f"passive-counterfeit-{uuid.uuid4()}@example.test",
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


def test_real_ocr_passive_counterfeit_becomes_high_risk(app: Flask) -> None:
    assert shutil.which(app.config["TESSERACT_CMD"]) is not None
    client = app.test_client()
    owner = _register(client)
    uploaded = client.post(
        "/api/v1/transactions",
        data={
            "receipt": (
                io.BytesIO(generated_passive_counterfeit_png()),
                "generated-passive-counterfeit.png",
                "image/png",
            ),
            "source": "GALLERY",
        },
        headers=_headers(owner, f"upload-{uuid.uuid4()}"),
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 201, uploaded.get_data(as_text=True)
    transaction_id = uploaded.json["data"]["transaction"]["id"]

    response = client.post(
        f"/api/v1/transactions/{transaction_id}/ocr",
        headers=_headers(owner, f"ocr-{uuid.uuid4()}"),
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    result = response.json["data"]
    assert result["status"] in {"OCR_READY", "OCR_PARTIAL"}
    assert "OCR_ENGINE_UNAVAILABLE" not in result["warnings"]
    preview = result["fraud_preview"]
    assert preview["class"] == "FRAUDULENT"
    assert preview["score_is_probability"] is False
    assert {
        "NUMERIC_SENDER_TRANSACTION_CLAIM",
        "GENUINE_TEMPLATE_ANOMALY",
    } <= set(preview["reason_codes"])
    assert preview["evidence"]["sender"]["sender_kind"] == "phone_number"
    assert preview["evidence"]["consensus"]["candidate_count"] > 1
    assert preview["evidence"]["format_profile"]["status"] == "AVAILABLE"
    assert "bbox" not in str(preview["evidence"])


@pytest.mark.parametrize(
    ("fixture_name", "fixture_factory", "expected_sender_kind"),
    (
        ("genuine-cash-in", generated_genuine_cash_in_png, "alphanumeric_provider"),
        (
            "genuine-payment-made",
            generated_genuine_payment_made_png,
            "alphanumeric_provider",
        ),
        (
            "genuine-cash-in-one-typo",
            generated_genuine_cash_in_one_typo_png,
            "alphanumeric_provider",
        ),
        ("official-advisory", generated_official_advisory_png, "alphanumeric_provider"),
        (
            "numeric-sender-ordinary-chat",
            generated_numeric_sender_ordinary_chat_png,
            "phone_number",
        ),
        ("body-phone-unknown-sender", generated_body_phone_unknown_sender_png, "unknown"),
    ),
)
def test_real_ocr_safe_boundaries_are_not_fraudulent(
    app: Flask,
    fixture_name: str,
    fixture_factory: Callable[[], bytes],
    expected_sender_kind: str,
) -> None:
    assert shutil.which(app.config["TESSERACT_CMD"]) is not None
    client = app.test_client()
    owner = _register(client)
    uploaded = client.post(
        "/api/v1/transactions",
        data={
            "receipt": (
                io.BytesIO(fixture_factory()),
                f"generated-{fixture_name}.png",
                "image/png",
            ),
            "source": "GALLERY",
        },
        headers=_headers(owner, f"upload-{uuid.uuid4()}"),
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 201, uploaded.get_data(as_text=True)
    transaction_id = uploaded.json["data"]["transaction"]["id"]

    response = client.post(
        f"/api/v1/transactions/{transaction_id}/ocr",
        headers=_headers(owner, f"ocr-{uuid.uuid4()}"),
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    preview = response.json["data"]["fraud_preview"]
    assert preview["class"] != "FRAUDULENT", preview
    assert "NUMERIC_SENDER_TRANSACTION_CLAIM" not in preview["reason_codes"]
    assert preview["evidence"]["sender"]["sender_kind"] == expected_sender_kind
    if fixture_name == "official-advisory":
        assert "PIN_OR_OTP_REQUEST" not in preview["reason_codes"]
