from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from flask import Flask
from tests.factories import create_complete_graph

from momo_fdvs.extensions import db
from momo_fdvs.models import Role, User, UserRole
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


def _staff(app: Flask, client: Any, role: str) -> dict[str, Any]:
    email = f"operations-{role.lower()}-{uuid.uuid4()}@example.test"
    with app.app_context():
        user = User(
            email=email,
            password_hash=hash_password(TEST_CREDENTIAL),
            full_name=f"Operations {role.title()}",
            status="ACTIVE",
            password_changed_at=datetime.now(UTC),
        )
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_code=role, granted_at=datetime.now(UTC)))
        db.session.commit()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": TEST_CREDENTIAL},
        headers={"X-Client-Type": "mobile"},
    )
    assert response.status_code == 200
    return response.json["data"]


def _headers(session: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


def test_staff_dashboard_and_masked_transaction_views(app: Flask) -> None:
    client = app.test_client()
    with app.app_context():
        graph = create_complete_graph(db.session)
        graph["transaction"].latest_analysis_run_id = graph["run"].id
        db.session.commit()
        transaction_id = graph["transaction"].id
    investigator = _staff(app, client, "INVESTIGATOR")

    dashboard = client.get("/api/v1/admin/dashboard", headers=_headers(investigator))
    assert dashboard.status_code == 200, dashboard.get_data(as_text=True)
    data = dashboard.json["data"]
    assert set(data) == {
        "risk_counts",
        "verification_counts",
        "case_status_counts",
        "case_source_counts",
        "analysis_status_counts",
        "processing_duration_ms",
        "active_versions",
        "recent_activity",
    }
    assert data["risk_counts"]
    assert data["verification_counts"]

    listed = client.get("/api/v1/admin/transactions", headers=_headers(investigator))
    assert listed.status_code == 200
    assert listed.json["data"]["total"] >= 1
    item = next(row for row in listed.json["data"]["items"] if row["id"] == str(transaction_id))
    assert item["id"] == str(transaction_id)
    assert item["analysis"]["risk_band"]
    serialized = listed.get_data(as_text=True).lower()
    assert "object_key" not in serialized
    assert "raw_text" not in serialized
    assert "confirmed_fields" not in serialized
    assert "user_id" not in serialized

    detail = client.get(
        f"/api/v1/admin/transactions/{transaction_id}", headers=_headers(investigator)
    )
    assert detail.status_code == 200
    assert detail.json["data"]["automated_evidence_immutable"] is True
    assert detail.json["data"]["receipt_available"] is True


def test_admin_operational_security_and_readiness_views(app: Flask) -> None:
    client = app.test_client()
    with app.app_context():
        graph = create_complete_graph(db.session)
        db.session.commit()
        model_id = graph["model"].id
        rule_set_id = graph["rule_set"].id
    admin = _staff(app, client, "ADMIN")
    investigator = _staff(app, client, "INVESTIGATOR")

    audit = client.get("/api/v1/admin/audit-logs", headers=_headers(admin))
    assert audit.status_code == 200
    audit_text = audit.get_data(as_text=True).lower()
    assert "metadata" not in audit_text
    assert "ip_hash" not in audit_text
    assert "user_agent_hash" not in audit_text
    assert client.get("/api/v1/admin/audit-logs", headers=_headers(investigator)).status_code == 403

    status = client.get("/api/v1/admin/system-status", headers=_headers(admin))
    assert status.status_code == 200
    components = status.json["data"]["components"]
    assert set(components) >= {
        "database",
        "storage",
        "tesseract",
        "image_model",
        "structured_model",
        "notification_adapter",
    }
    status_text = status.get_data(as_text=True).lower()
    assert "password" not in status_text
    assert "local_private_storage_root" not in status_text
    assert "artifact_uri" not in status_text

    models = client.get("/api/v1/admin/models", headers=_headers(admin))
    assert models.status_code == 200
    assert models.json["data"]["total"] >= 1
    model_text = models.get_data(as_text=True).lower()
    assert "artifact_uri" not in model_text
    assert "model_card_key" not in model_text
    model_detail = client.get(f"/api/v1/admin/models/{model_id}", headers=_headers(admin))
    assert model_detail.status_code == 200
    assert "artifact_uri" not in model_detail.get_data(as_text=True).lower()

    rules = client.get("/api/v1/admin/rule-sets", headers=_headers(admin))
    assert rules.status_code == 200
    assert rules.json["data"]["total"] >= 1
    rule_text = rules.get_data(as_text=True).lower()
    assert "risk_weights" not in rule_text
    assert "thresholds" not in rule_text
    rule_detail = client.get(f"/api/v1/admin/rule-sets/{rule_set_id}", headers=_headers(admin))
    assert rule_detail.status_code == 200
    assert "condition" not in rule_detail.get_data(as_text=True).lower()

    reports = client.get("/api/v1/admin/reports", headers=_headers(investigator))
    assert reports.status_code == 200
    reports_text = reports.get_data(as_text=True).lower()
    assert "object_key" not in reports_text
    assert all(item["report_type"] == "CASE" for item in reports.json["data"]["items"])

    assert client.get("/api/v1/admin/system-status").status_code == 401
