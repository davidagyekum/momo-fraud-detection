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


def test_rejects_invalid_environment() -> None:
    with pytest.raises(ConfigurationError, match="APP_ENV"):
        load_config("demo")
