"""Environment-backed Flask configuration with fail-fast validation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class ConfigurationError(RuntimeError):
    """Raised when the runtime environment violates the configuration contract."""


def _boolean(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be a boolean value")


def _integer(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}")
    return value


def _origins() -> list[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8081")
    origins = [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    if not origins:
        raise ConfigurationError("CORS_ALLOWED_ORIGINS must contain at least one explicit origin")
    if "*" in origins:
        raise ConfigurationError("Wildcard CORS origins are prohibited")
    for origin in origins:
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigurationError("CORS_ALLOWED_ORIGINS contains an invalid origin")
    return origins


def _database_url(environment: str) -> str:
    default = "postgresql+psycopg://momo_fdvs:momo_fdvs_local_only@localhost:5432/momo_fdvs"
    value = os.getenv("DATABASE_URL", default if environment != "production" else "")
    if not value:
        raise ConfigurationError("DATABASE_URL is required")
    if environment != "testing" and not value.startswith("postgresql+psycopg://"):
        raise ConfigurationError("DATABASE_URL must use the postgresql+psycopg driver")
    return value


def load_config(config_name: str | None = None) -> dict[str, Any]:
    """Load a fresh config mapping so tests and workers never share stale environment state."""
    environment = (config_name or os.getenv("APP_ENV") or "development").strip().lower()
    if environment not in {"development", "testing", "production"}:
        raise ConfigurationError("APP_ENV must be development, testing or production")

    credentials = _boolean("CORS_ALLOW_CREDENTIALS", True)
    origins = _origins()
    if credentials and "*" in origins:
        raise ConfigurationError("Credentialed CORS requires explicit origins")

    repository_root = Path(__file__).resolve().parents[4]
    storage_root = Path(
        os.getenv("LOCAL_PRIVATE_STORAGE_ROOT", str(repository_root / ".local" / "private-storage"))
    ).resolve()
    storage_adapter = os.getenv("STORAGE_ADAPTER", "local").strip().lower()
    if storage_adapter not in {"local", "s3"}:
        raise ConfigurationError("STORAGE_ADAPTER must be local or s3")
    s3_bucket = os.getenv("S3_BUCKET", "").strip()
    if storage_adapter == "s3" and not s3_bucket:
        raise ConfigurationError("S3_BUCKET is required when STORAGE_ADAPTER=s3")
    migrations_dir = Path(
        os.getenv(
            "MIGRATIONS_DIR",
            str(Path(__file__).resolve().parents[2] / "migrations"),
        )
    ).resolve()

    return {
        "ENVIRONMENT": environment,
        "TESTING": environment == "testing",
        "DEBUG": environment == "development" and _boolean("FLASK_DEBUG", False),
        "APP_NAME": os.getenv("APP_NAME", "MoMo-FDVS"),
        "APP_VERSION": os.getenv("APP_VERSION", "0.1.0-dev"),
        "APP_BUILD_SHA": os.getenv("APP_BUILD_SHA", "local"),
        "API_CONTRACT_VERSION": os.getenv("API_CONTRACT_VERSION", "1.0.0"),
        "REQUEST_ID_HEADER": "X-Request-ID",
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO").upper(),
        "SQLALCHEMY_DATABASE_URI": _database_url(environment),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "pool_pre_ping": True,
            "pool_size": _integer("DATABASE_POOL_SIZE", 5),
            "max_overflow": _integer("DATABASE_POOL_MAX_OVERFLOW", 5, minimum=0),
            "pool_timeout": _integer("DATABASE_POOL_TIMEOUT_SECONDS", 30),
        },
        "MIGRATIONS_DIR": str(migrations_dir),
        "LOCAL_PRIVATE_STORAGE_ROOT": storage_root,
        "STORAGE_ADAPTER": storage_adapter,
        "S3_ENDPOINT_URL": os.getenv("S3_ENDPOINT_URL") or None,
        "S3_REGION": os.getenv("S3_REGION") or None,
        "S3_BUCKET": s3_bucket,
        "S3_PREFIX": os.getenv("S3_PREFIX", "momo-fdvs").strip("/"),
        "S3_ACCESS_KEY_ID": os.getenv("S3_ACCESS_KEY_ID") or None,
        "S3_SECRET_ACCESS_KEY": os.getenv("S3_SECRET_ACCESS_KEY") or None,
        "S3_SERVER_SIDE_ENCRYPTION": os.getenv("S3_SERVER_SIDE_ENCRYPTION", "AES256"),
        "SIGNED_URL_TTL_SECONDS": _integer("SIGNED_URL_TTL_SECONDS", 300),
        "TESSERACT_CMD": os.getenv("TESSERACT_CMD", "tesseract"),
        "CORS_ALLOWED_ORIGINS": origins,
        "CORS_ALLOW_CREDENTIALS": credentials,
        "API_TITLE": "MoMo-FDVS API",
        "API_VERSION": "v1",
        "OPENAPI_VERSION": "3.0.3",
        "OPENAPI_URL_PREFIX": "/api/v1",
        "OPENAPI_JSON_PATH": "openapi.json",
        "OPENAPI_SWAGGER_UI_PATH": None,
    }
