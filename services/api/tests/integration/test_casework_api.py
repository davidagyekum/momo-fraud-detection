from __future__ import annotations

import hashlib
import os
import uuid
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from flask import Flask
from sqlalchemy import select
from tests.factories import create_complete_graph

from momo_fdvs.extensions import db
from momo_fdvs.models import (
    AnalysisRun,
    AuditLog,
    CaseDecision,
    CaseEvent,
    FraudCase,
    Notification,
    ReportArtifact,
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


def _headers(session: dict[str, Any], key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def _login(client: Any, user: User) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": str(user.email), "password": TEST_CREDENTIAL},
        headers={"X-Client-Type": "mobile"},
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    return cast(dict[str, Any], response.json["data"])


def _analysed_owner(
    app: Flask,
    client: Any,
    *,
    risk_summary: str = "Controlled incomplete evidence.",
) -> tuple[dict[str, Any], uuid.UUID, uuid.UUID]:
    with app.app_context():
        graph = create_complete_graph(db.session)
        user = cast(User, graph["user"])
        transaction = cast(Transaction, graph["transaction"])
        run = cast(AnalysisRun, graph["run"])
        existing_case = cast(FraudCase, graph["case"])
        existing_notification = cast(Notification, graph["notification"])
        db.session.delete(existing_case)
        db.session.delete(existing_notification)
        user.password_hash = hash_password(TEST_CREDENTIAL)
        user.status = "ACTIVE"
        db.session.add(UserRole(user_id=user.id, role_code="USER", granted_at=datetime.now(UTC)))
        run.status = "PARTIAL"
        run.completed_at = datetime.now(UTC)
        run.component_scores = {
            "policy": {
                "status": "PARTIAL",
                "band": "inconclusive",
                "summary": risk_summary,
                "policy_version": "controlled-policy-v1",
            }
        }
        transaction.status = "PARTIAL"
        transaction.latest_analysis_run_id = run.id
        db.session.commit()
        transaction_id = transaction.id
        run_id = run.id
        session = _login(client, user)
    return session, transaction_id, run_id


def _staff(app: Flask, client: Any, role: str) -> tuple[dict[str, Any], uuid.UUID]:
    with app.app_context():
        user = User(
            email=f"casework-{role.lower()}-{uuid.uuid4()}@example.test",
            password_hash=hash_password(TEST_CREDENTIAL),
            full_name=f"Casework {role.title()}",
            status="ACTIVE",
            password_changed_at=datetime.now(UTC),
        )
        db.session.add(user)
        db.session.flush()
        db.session.add(UserRole(user_id=user.id, role_code=role, granted_at=datetime.now(UTC)))
        db.session.commit()
        user_id = user.id
        session = _login(client, user)
    return session, user_id


def _open_case(client: Any, owner: dict[str, Any], transaction_id: uuid.UUID) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/transactions/{transaction_id}/fraud-reports",
        headers=_headers(owner, f"case-{uuid.uuid4()}"),
        json={
            "category": "PAYMENT_NOT_RECEIVED",
            "description": "The expected controlled payment did not arrive.",
        },
    )
    assert response.status_code == 201, response.get_data(as_text=True)
    return cast(dict[str, Any], response.json["data"])


def test_owner_creates_replays_and_reads_limited_case(app: Flask) -> None:
    client = app.test_client()
    owner, transaction_id, _run_id = _analysed_owner(app, client)
    key = f"case-{uuid.uuid4()}"
    payload = {
        "category": "PAYMENT_NOT_RECEIVED",
        "description": "The expected controlled payment did not arrive.",
    }

    missing_key = client.post(
        f"/api/v1/transactions/{transaction_id}/fraud-reports",
        headers=_headers(owner),
        json=payload,
    )
    assert missing_key.status_code == 400
    assert missing_key.json["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    created = client.post(
        f"/api/v1/transactions/{transaction_id}/fraud-reports",
        headers=_headers(owner, key),
        json=payload,
    )
    assert created.status_code == 201, created.get_data(as_text=True)
    case = created.json["data"]
    case_id = case["id"]
    assert case["status"] == "OPEN"
    assert case["version"] == 1
    assert case["replayed"] is False
    assert case["linked_existing"] is False

    replay = client.post(
        f"/api/v1/transactions/{transaction_id}/fraud-reports",
        headers=_headers(owner, key),
        json=payload,
    )
    assert replay.status_code == 200
    assert replay.json["data"]["id"] == case_id
    assert replay.json["data"]["replayed"] is True

    reused = client.post(
        f"/api/v1/transactions/{transaction_id}/fraud-reports",
        headers=_headers(owner, key),
        json={"category": "OTHER", "description": "Different request."},
    )
    assert reused.status_code == 409
    assert reused.json["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"

    detail = client.get(f"/api/v1/fraud-reports/{case_id}", headers=_headers(owner))
    assert detail.status_code == 200
    projection = detail.json["data"]
    assert projection["transaction_id"] == str(transaction_id)
    assert projection["timeline"][0]["event_type"] == "OPENED"
    serialized = detail.get_data(as_text=True).lower()
    assert "assigned_to" not in serialized
    assert "metadata" not in serialized
    assert "object_key" not in serialized

    with app.app_context():
        case_uuid = uuid.UUID(case_id)
        persisted_cases = db.session.scalars(
            select(FraudCase).where(FraudCase.id == case_uuid)
        ).all()
        assert len(persisted_cases) == 1
        assert (
            len(db.session.scalars(select(CaseEvent).where(CaseEvent.case_id == case_uuid)).all())
            == 1
        )
        assert (
            len(
                db.session.scalars(
                    select(Notification).where(
                        Notification.user_id == uuid.UUID(owner["user"]["id"]),
                        Notification.target_id == case_uuid,
                    )
                ).all()
            )
            == 1
        )
        assert (
            db.session.scalar(
                select(AuditLog).where(
                    AuditLog.action == "case.opened", AuditLog.target_id == case_uuid
                )
            )
            is not None
        )


def test_owner_case_scope_and_analysis_requirement(app: Flask) -> None:
    client = app.test_client()
    owner, transaction_id, _run_id = _analysed_owner(app, client)
    outsider, outsider_transaction_id, _outsider_run_id = _analysed_owner(app, client)

    foreign = client.post(
        f"/api/v1/transactions/{transaction_id}/fraud-reports",
        headers=_headers(outsider, f"case-{uuid.uuid4()}"),
        json={"category": "OTHER"},
    )
    assert foreign.status_code == 404

    with app.app_context():
        outsider_id = uuid.UUID(outsider["user"]["id"])
        unanalysed = Transaction(user_id=outsider_id, status="READY")
        db.session.add(unanalysed)
        db.session.commit()
        unanalysed_id = unanalysed.id

    no_analysis = client.post(
        f"/api/v1/transactions/{unanalysed_id}/fraud-reports",
        headers=_headers(outsider, f"case-{uuid.uuid4()}"),
        json={"category": "OTHER"},
    )
    assert no_analysis.status_code == 409
    assert no_analysis.json["error"]["code"] == "ANALYSIS_REQUIRED"

    created = _open_case(client, owner, transaction_id)
    denied = client.get(f"/api/v1/fraud-reports/{created['id']}", headers=_headers(outsider))
    assert denied.status_code == 404
    assert outsider_transaction_id != transaction_id


def test_owner_links_existing_active_case_across_sources(app: Flask) -> None:
    client = app.test_client()
    owner, transaction_id, _run_id = _analysed_owner(app, client)
    with app.app_context():
        existing = FraudCase(
            transaction_id=transaction_id,
            source="AUTO_HIGH_RISK",
            category="OTHER",
            status="OPEN",
            version=1,
            opened_at=datetime.now(UTC),
        )
        db.session.add(existing)
        db.session.commit()
        existing_id = existing.id

    linked = client.post(
        f"/api/v1/transactions/{transaction_id}/fraud-reports",
        headers=_headers(owner, f"case-{uuid.uuid4()}"),
        json={"category": "ALTERED_RECEIPT"},
    )
    assert linked.status_code == 200
    assert linked.json["data"]["id"] == str(existing_id)
    assert linked.json["data"]["linked_existing"] is True
    assert linked.json["data"]["replayed"] is False

    detail = client.get(f"/api/v1/fraud-reports/{existing_id}", headers=_headers(owner))
    assert detail.status_code == 200
    assert detail.json["data"]["source"] == "AUTO_HIGH_RISK"
    with app.app_context():
        cases = db.session.scalars(
            select(FraudCase).where(FraudCase.transaction_id == transaction_id)
        ).all()
        assert len(cases) == 1


def test_investigator_case_state_machine_and_immutable_analysis(app: Flask) -> None:
    client = app.test_client()
    owner, transaction_id, run_id = _analysed_owner(app, client)
    investigator, investigator_id = _staff(app, client, "INVESTIGATOR")
    admin, _admin_id = _staff(app, client, "ADMIN")
    case = _open_case(client, owner, transaction_id)
    case_id = case["id"]

    listed = client.get("/api/v1/admin/cases?status=OPEN", headers=_headers(investigator))
    assert listed.status_code == 200
    assert any(item["id"] == case_id for item in listed.json["data"]["items"])

    admin_detail = client.get(f"/api/v1/admin/cases/{case_id}", headers=_headers(admin))
    assert admin_detail.status_code == 200
    assert admin_detail.json["data"]["automated_evidence"]["immutable"] is True

    assigned = client.post(
        f"/api/v1/admin/cases/{case_id}/assign",
        headers=_headers(admin),
        json={"investigator_id": str(investigator_id), "expected_case_version": 1},
    )
    assert assigned.status_code == 200
    assert assigned.json["data"]["status"] == "ASSIGNED"
    assert assigned.json["data"]["version"] == 2

    stale = client.post(
        f"/api/v1/admin/cases/{case_id}/start-review",
        headers=_headers(investigator),
        json={"expected_case_version": 1},
    )
    assert stale.status_code == 409
    assert stale.json["error"]["code"] == "CASE_VERSION_CONFLICT"

    review = client.post(
        f"/api/v1/admin/cases/{case_id}/start-review",
        headers=_headers(investigator),
        json={"expected_case_version": 2},
    )
    assert review.status_code == 200
    assert review.json["data"]["status"] == "IN_REVIEW"
    assert review.json["data"]["version"] == 3

    note = client.post(
        f"/api/v1/admin/cases/{case_id}/notes",
        headers=_headers(investigator),
        json={
            "note": "Controlled note without private receipt values.",
            "expected_case_version": 3,
        },
    )
    assert note.status_code == 200
    assert note.json["data"]["version"] == 4

    decision = client.post(
        f"/api/v1/admin/cases/{case_id}/decisions",
        headers=_headers(investigator),
        json={
            "outcome": "ESCALATED",
            "reason": "Stored-reference details conflict with the confirmed receipt fields.",
            "expected_case_version": 4,
        },
    )
    assert decision.status_code == 200
    assert decision.json["data"]["status"] == "DECIDED"
    assert decision.json["data"]["version"] == 5
    assert decision.json["data"]["decision"]["outcome"] == "ESCALATED"

    invalid = client.post(
        f"/api/v1/admin/cases/{case_id}/notes",
        headers=_headers(investigator),
        json={"note": "Too late.", "expected_case_version": 5},
    )
    assert invalid.status_code == 409
    assert invalid.json["error"]["code"] == "CASE_TRANSITION_INVALID"

    with app.app_context():
        persisted_run = db.session.get(AnalysisRun, run_id)
        persisted_case = db.session.get(FraudCase, uuid.UUID(case_id))
        assert persisted_run is not None and persisted_run.status == "PARTIAL"
        assert persisted_case is not None and persisted_case.status == "DECIDED"
        assert len(persisted_case.events) == 5
        decisions = db.session.scalars(
            select(CaseDecision).where(CaseDecision.case_id == persisted_case.id)
        ).all()
        assert len(decisions) == 1
        assert (
            db.session.scalar(
                select(AuditLog).where(
                    AuditLog.action == "case.decision_recorded",
                    AuditLog.target_id == persisted_case.id,
                )
            )
            is not None
        )


def test_notification_inbox_is_owner_scoped_and_read_actions_are_idempotent(
    app: Flask,
) -> None:
    client = app.test_client()
    owner, transaction_id, _run_id = _analysed_owner(app, client)
    outsider, outsider_transaction_id, _outsider_run_id = _analysed_owner(app, client)
    owner_case = _open_case(client, owner, transaction_id)
    _open_case(client, outsider, outsider_transaction_id)

    inbox = client.get("/api/v1/notifications?unread=true", headers=_headers(owner))
    assert inbox.status_code == 200, inbox.get_data(as_text=True)
    items = inbox.json["data"]["items"]
    assert inbox.json["data"]["total"] == 1
    assert len(items) == 1
    notification = items[0]
    assert notification["target"] == {"type": "CASE", "id": owner_case["id"]}
    assert "delivery_status" not in notification
    assert "dedupe_key" not in notification

    count = client.get("/api/v1/notifications/unread-count", headers=_headers(owner))
    assert count.status_code == 200
    assert count.json["data"]["unread_count"] == 1

    denied = client.post(
        f"/api/v1/notifications/{notification['id']}/read",
        headers=_headers(outsider),
    )
    assert denied.status_code == 404

    read = client.post(
        f"/api/v1/notifications/{notification['id']}/read",
        headers=_headers(owner),
    )
    assert read.status_code == 200
    assert read.json["data"]["read_at"] is not None
    replay = client.post(
        f"/api/v1/notifications/{notification['id']}/read",
        headers=_headers(owner),
    )
    assert replay.status_code == 200
    assert replay.json["data"]["read_at"] == read.json["data"]["read_at"]

    read_all = client.post("/api/v1/notifications/read-all", headers=_headers(owner))
    assert read_all.status_code == 200
    assert read_all.json["data"] == {"marked_read": 0, "unread_count": 0}
    count_after = client.get("/api/v1/notifications/unread-count", headers=_headers(owner))
    assert count_after.json["data"]["unread_count"] == 0


def test_owner_report_is_escaped_hashed_private_and_replayed(app: Flask) -> None:
    client = app.test_client()
    owner, transaction_id, run_id = _analysed_owner(
        app,
        client,
        risk_summary='<script>alert("private")</script>',
    )
    outsider, _outsider_transaction_id, _outsider_run_id = _analysed_owner(app, client)

    missing_key = client.post(
        f"/api/v1/transactions/{transaction_id}/reports",
        headers=_headers(owner),
        json={"format": "HTML"},
    )
    assert missing_key.status_code == 400
    assert missing_key.json["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    key = f"report-{uuid.uuid4()}"
    created = client.post(
        f"/api/v1/transactions/{transaction_id}/reports",
        headers=_headers(owner, key),
        json={"format": "HTML"},
    )
    assert created.status_code == 201, created.get_data(as_text=True)
    report = created.json["data"]
    assert report["status"] == "READY"
    assert report["replayed"] is False
    assert report["download_url"] == f"/api/v1/reports/{report['id']}/download"
    assert "object_key" not in created.get_data(as_text=True)

    replay = client.post(
        f"/api/v1/transactions/{transaction_id}/reports",
        headers=_headers(owner, key),
        json={"format": "HTML"},
    )
    assert replay.status_code == 200
    assert replay.json["data"]["id"] == report["id"]
    assert replay.json["data"]["replayed"] is True

    denied = client.get(f"/api/v1/reports/{report['id']}/download", headers=_headers(outsider))
    assert denied.status_code == 404

    downloaded = client.get(f"/api/v1/reports/{report['id']}/download", headers=_headers(owner))
    assert downloaded.status_code == 200, downloaded.get_data(as_text=True)
    assert downloaded.headers["Cache-Control"].startswith("private, no-store")
    assert downloaded.headers["Pragma"] == "no-cache"
    assert downloaded.headers["X-Content-Type-Options"] == "nosniff"
    assert downloaded.headers["Content-Security-Policy"] == "sandbox; default-src 'none'"
    assert "attachment" in downloaded.headers["Content-Disposition"]
    html_report = downloaded.get_data(as_text=True)
    assert "&lt;script&gt;" in html_report
    assert "<script>" not in html_report
    assert "Fraud-risk assessment" in html_report
    assert "Transaction verification" in html_report
    assert "not a live confirmation" in html_report

    with app.app_context():
        artifact = db.session.get(ReportArtifact, uuid.UUID(report["id"]))
        assert artifact is not None
        assert artifact.owner_user_id == uuid.UUID(owner["user"]["id"])
        assert artifact.analysis_run_id == run_id
        assert artifact.sha256 == hashlib.sha256(downloaded.data).hexdigest()
        assert artifact.object_key not in html_report
