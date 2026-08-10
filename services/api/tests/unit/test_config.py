from __future__ import annotations

import pytest

from momo_fdvs.config import ConfigurationError, load_config


def test_rejects_wildcard_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    with pytest.raises(ConfigurationError, match="Wildcard"):
        load_config("development")


def test_production_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        load_config("production")


def test_rejects_non_postgresql_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///not-production.db")
    with pytest.raises(ConfigurationError, match="postgresql"):
        load_config("development")


def test_rejects_invalid_boolean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "sometimes")
    with pytest.raises(ConfigurationError, match="boolean"):
        load_config("development")


def test_rejects_invalid_pool_size(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_POOL_SIZE", "many")
    with pytest.raises(ConfigurationError, match="integer"):
        load_config("development")


def test_rejects_invalid_ocr_confidence_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OCR_REVIEW_CONFIDENCE_THRESHOLD", "1.5")
    with pytest.raises(ConfigurationError, match="between"):
        load_config("development")


def test_loads_bounded_ocr_configuration() -> None:
    config = load_config("testing")
    assert config["OCR_REVIEW_CONFIDENCE_THRESHOLD"] == 0.75
    assert config["OCR_PIPELINE_VERSION"] == "ocr-pipeline-v1"
    assert config["OCR_PARSER_VERSION"] == "generic-parser-v1"
    assert config["OCR_FIELD_SCHEMA_VERSION"] == "ocr-fields-v1"


def test_request_limit_must_exceed_receipt_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UPLOAD_MAX_BYTES", "1000")
    monkeypatch.setenv("UPLOAD_REQUEST_MAX_BYTES", "1000")
    with pytest.raises(ConfigurationError, match="UPLOAD_REQUEST_MAX_BYTES"):
        load_config("development")


def test_rejects_invalid_environment() -> None:
    with pytest.raises(ConfigurationError, match="APP_ENV"):
        load_config("demo")


def test_production_requires_non_placeholder_auth_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://momo_fdvs:local-only@database/momo_fdvs"
    )
    for name in ("JWT_ACCESS_SECRET", "JWT_REFRESH_SECRET", "CSRF_SECRET"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ConfigurationError, match="JWT_ACCESS_SECRET"):
        load_config("production")


def test_cross_site_cookie_requires_secure_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_COOKIE_SAMESITE", "None")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    with pytest.raises(ConfigurationError, match="AUTH_COOKIE_SECURE"):
        load_config("development")


def test_rejects_invalid_cookie_same_site(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_COOKIE_SAMESITE", "sometimes")
    with pytest.raises(ConfigurationError, match="AUTH_COOKIE_SAMESITE"):
        load_config("development")


def test_csrf_cookie_is_browser_readable_from_portal_routes() -> None:
    config = load_config("testing")
    assert config["AUTH_COOKIE_PATH"] == "/api/v1/auth"
    assert config["AUTH_CSRF_COOKIE_PATH"] == "/"
