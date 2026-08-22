from __future__ import annotations

import io
import os
import shutil
import uuid
from typing import Any

import pytest
from flask import Flask
from tests.fixtures.generated_passive_counterfeit import (
    generated_passive_counterfeit_png,
)

from momo_fdvs.extensions import db
from momo_fdvs.models import Role

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
