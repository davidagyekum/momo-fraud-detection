from __future__ import annotations

from unittest.mock import Mock
from uuid import UUID

from flask import Flask
from sqlalchemy.exc import OperationalError


def test_health_is_versioned_and_contains_no_secret(app: Flask) -> None:
    response = app.test_client().get("/api/v1/health")
    assert response.status_code == 200
    assert response.json["data"] == {
        "status": "ok",
        "service": "momo-fdvs-api",
        "version": "0.1.0-test",
    }
    serialized = response.get_data(as_text=True).lower()
    assert "password" not in serialized
    assert "database_url" not in serialized
    UUID(response.headers["X-Request-ID"])


def test_valid_request_id_is_echoed(app: Flask) -> None:
    request_id = "4e01ec26-3e79-4b88-bbbe-97f62ca24557"
    response = app.test_client().get("/api/v1/version", headers={"X-Request-ID": request_id})
    assert response.headers["X-Request-ID"] == request_id
    assert response.json["meta"]["request_id"] == request_id


def test_invalid_request_id_is_replaced(app: Flask) -> None:
    response = app.test_client().get(
        "/api/v1/version", headers={"X-Request-ID": "not-a-valid-correlation-id"}
    )
    assert response.headers["X-Request-ID"] != "not-a-valid-correlation-id"
    UUID(response.headers["X-Request-ID"])


def test_unknown_route_uses_standard_error_envelope(app: Flask) -> None:
    response = app.test_client().get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json["error"]["code"] == "NOT_FOUND"
    assert response.json["error"]["request_id"] == response.headers["X-Request-ID"]


def test_ready_passes_when_core_dependencies_are_available(app: Flask, monkeypatch) -> None:
    execute = Mock(return_value=Mock())
    monkeypatch.setattr("momo_fdvs.readiness.db.session.execute", execute)
    monkeypatch.setattr("momo_fdvs.readiness.shutil.which", lambda _command: None)

    response = app.test_client().get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json["data"]["ready"] is True
    assert response.json["data"]["components"]["database"]["status"] == "ready"
    assert response.json["data"]["components"]["tesseract"]["status"] == "degraded"
    assert response.json["data"]["analysis_available"] is False


def test_ready_fails_safely_when_database_is_unavailable(app: Flask, monkeypatch) -> None:
    error = OperationalError("SELECT 1", {}, RuntimeError("connection refused"))
    monkeypatch.setattr("momo_fdvs.readiness.db.session.execute", Mock(side_effect=error))
    monkeypatch.setattr("momo_fdvs.readiness.db.session.rollback", Mock())

    response = app.test_client().get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json["data"]["ready"] is False
    assert response.json["data"]["components"]["database"] == {
        "status": "unavailable",
        "reason": "connection_failed",
    }
    assert "connection refused" not in response.get_data(as_text=True)


def test_ready_reports_safe_tesseract_version(app: Flask, monkeypatch) -> None:
    monkeypatch.setattr("momo_fdvs.readiness.db.session.execute", Mock(return_value=Mock()))
    monkeypatch.setattr("momo_fdvs.readiness.shutil.which", lambda _command: "tesseract")
    monkeypatch.setattr(
        "momo_fdvs.readiness.subprocess.run",
        Mock(return_value=Mock(returncode=0, stdout="tesseract 5.5.0\n", stderr="")),
    )

    response = app.test_client().get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json["data"]["components"]["tesseract"] == {
        "status": "ready",
        "version": "5.5.0",
    }
    assert response.json["data"]["analysis_available"] is True


def test_unexpected_errors_are_generic_and_correlated(app: Flask) -> None:
    @app.get("/api/v1/test-only-error")
    def raise_test_error() -> None:
        raise RuntimeError("private database path and credential")

    response = app.test_client().get("/api/v1/test-only-error")

    assert response.status_code == 500
    assert response.json["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert response.json["error"]["request_id"] == response.headers["X-Request-ID"]
    assert "private database path" not in response.get_data(as_text=True)
