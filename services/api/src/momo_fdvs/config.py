"""Environment-backed Flask configuration with fail-fast validation."""

from __future__ import annotations

import os
import re
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


def _float(name: str, default: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}")
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


def _secret(name: str, environment: str) -> str:
    value = os.getenv(name, "")
    if not value and environment != "production":
        value = f"momo_fdvs_local_only_{name.lower()}_minimum_32_chars"
    if len(value) < 32 or (environment == "production" and "CHANGE_ME" in value.upper()):
        raise ConfigurationError(
            f"{name} must be a non-placeholder value of at least 32 characters"
        )
    return value


def _rate_limit(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    if not re.fullmatch(r"\d+\s+per\s+(second|minute|hour|day)", value):
        raise ConfigurationError(f"{name} must use '<number> per <unit>' syntax")
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
    cookie_secure = _boolean("AUTH_COOKIE_SECURE", environment == "production")
    cookie_samesite = os.getenv("AUTH_COOKIE_SAMESITE", "Lax").strip().title()
    if cookie_samesite not in {"Strict", "Lax", "None"}:
        raise ConfigurationError("AUTH_COOKIE_SAMESITE must be Strict, Lax or None")
    if cookie_samesite == "None" and not cookie_secure:
        raise ConfigurationError("AUTH_COOKIE_SECURE must be true when AUTH_COOKIE_SAMESITE=None")
    migrations_dir = Path(
        os.getenv(
            "MIGRATIONS_DIR",
            str(Path(__file__).resolve().parents[2] / "migrations"),
        )
    ).resolve()
    upload_max_bytes = _integer("UPLOAD_MAX_BYTES", 10_485_760)
    upload_request_max_bytes = _integer("UPLOAD_REQUEST_MAX_BYTES", 11_534_336)
    if upload_request_max_bytes <= upload_max_bytes:
        raise ConfigurationError("UPLOAD_REQUEST_MAX_BYTES must exceed UPLOAD_MAX_BYTES")

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
        "JWT_ACCESS_SECRET": _secret("JWT_ACCESS_SECRET", environment),
        "JWT_REFRESH_SECRET": _secret("JWT_REFRESH_SECRET", environment),
        "CSRF_SECRET": _secret("CSRF_SECRET", environment),
        "ACCESS_TOKEN_TTL_MINUTES": _integer("ACCESS_TOKEN_TTL_MINUTES", 15),
        "REFRESH_TOKEN_TTL_DAYS": _integer("REFRESH_TOKEN_TTL_DAYS", 7),
        "PASSWORD_RESET_TTL_MINUTES": _integer("PASSWORD_RESET_TTL_MINUTES", 30),
        "AUTH_COOKIE_NAME": os.getenv("AUTH_COOKIE_NAME", "momo_fdvs_refresh"),
        "AUTH_COOKIE_SECURE": cookie_secure,
        "AUTH_COOKIE_SAMESITE": cookie_samesite,
        "AUTH_COOKIE_DOMAIN": os.getenv("AUTH_COOKIE_DOMAIN") or None,
        "AUTH_COOKIE_PATH": os.getenv("AUTH_COOKIE_PATH", "/api/v1/auth"),
        "AUTH_CSRF_COOKIE_PATH": os.getenv("AUTH_CSRF_COOKIE_PATH", "/"),
        "SELF_REGISTRATION_ENABLED": _boolean("SELF_REGISTRATION_ENABLED", True),
        "RATELIMIT_STORAGE_URI": os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
        "RATE_LIMIT_LOGIN": _rate_limit("RATE_LIMIT_LOGIN", "5 per minute"),
        "RATE_LIMIT_REFRESH": _rate_limit("RATE_LIMIT_REFRESH", "10 per minute"),
        "RATE_LIMIT_PASSWORD_RESET": _rate_limit("RATE_LIMIT_PASSWORD_RESET", "5 per hour"),
        "RATE_LIMIT_REGISTRATION": _rate_limit("RATE_LIMIT_REGISTRATION", "5 per hour"),
        "RATE_LIMIT_UPLOAD": _rate_limit("RATE_LIMIT_UPLOAD", "30 per hour"),
        "RATE_LIMIT_RECEIPT_READ": _rate_limit("RATE_LIMIT_RECEIPT_READ", "60 per minute"),
        "RATE_LIMIT_OCR": _rate_limit("RATE_LIMIT_OCR", "10 per hour"),
        "RATE_LIMIT_OCR_REVIEW": _rate_limit("RATE_LIMIT_OCR_REVIEW", "60 per minute"),
        "RATE_LIMIT_REFERENCE_IMPORT": _rate_limit("RATE_LIMIT_REFERENCE_IMPORT", "20 per hour"),
        "UPLOAD_MAX_BYTES": upload_max_bytes,
        "UPLOAD_REQUEST_MAX_BYTES": upload_request_max_bytes,
        "MAX_CONTENT_LENGTH": upload_request_max_bytes,
        "UPLOAD_MAX_PIXEL_COUNT": _integer("UPLOAD_MAX_PIXEL_COUNT", 30_000_000),
        "UPLOAD_MAX_DIMENSION_PX": _integer("UPLOAD_MAX_DIMENSION_PX", 12_000),
        "UPLOAD_MIN_WIDTH_PX": _integer("UPLOAD_MIN_WIDTH_PX", 320),
        "UPLOAD_MIN_HEIGHT_PX": _integer("UPLOAD_MIN_HEIGHT_PX", 320),
        "UPLOAD_CLIENT_METADATA_MAX_BYTES": _integer("UPLOAD_CLIENT_METADATA_MAX_BYTES", 4_096),
        "UPLOAD_IDEMPOTENCY_TTL_HOURS": _integer("UPLOAD_IDEMPOTENCY_TTL_HOURS", 24),
        "UPLOAD_NEAR_DUPLICATE_DISTANCE": _integer("UPLOAD_NEAR_DUPLICATE_DISTANCE", 5, minimum=0),
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
        "TESSERACT_LANG": os.getenv("TESSERACT_LANG", "eng").strip(),
        "TESSERACT_TIMEOUT_SECONDS": _integer("TESSERACT_TIMEOUT_SECONDS", 20),
        "OCR_REVIEW_CONFIDENCE_THRESHOLD": _float("OCR_REVIEW_CONFIDENCE_THRESHOLD", 0.75),
        "OCR_MAX_VARIANTS": _integer("OCR_MAX_VARIANTS", 6),
        "OCR_TARGET_MIN_WIDTH_PX": _integer("OCR_TARGET_MIN_WIDTH_PX", 1_200),
        "OCR_PIPELINE_VERSION": os.getenv("OCR_PIPELINE_VERSION", "ocr-pipeline-v1").strip(),
        "OCR_PARSER_VERSION": os.getenv("OCR_PARSER_VERSION", "generic-parser-v1").strip(),
        "OCR_FIELD_SCHEMA_VERSION": os.getenv("OCR_FIELD_SCHEMA_VERSION", "ocr-fields-v1").strip(),
        "REFERENCE_AMOUNT_TOLERANCE": _float("REFERENCE_AMOUNT_TOLERANCE", 0.0, maximum=100.0),
        "REFERENCE_TIMESTAMP_TOLERANCE_MINUTES": _integer(
            "REFERENCE_TIMESTAMP_TOLERANCE_MINUTES", 30, minimum=0
        ),
        "REFERENCE_NAME_SIMILARITY_THRESHOLD": _float("REFERENCE_NAME_SIMILARITY_THRESHOLD", 0.90),
        "REFERENCE_IMPORT_MAX_BYTES": _integer("REFERENCE_IMPORT_MAX_BYTES", 10_485_760),
        "REFERENCE_IMPORT_MAX_ROWS": _integer("REFERENCE_IMPORT_MAX_ROWS", 100_000),
        "REFERENCE_IMPORT_PREVIEW_ERRORS": _integer("REFERENCE_IMPORT_PREVIEW_ERRORS", 100),
        "VERIFIER_VERSION": os.getenv("VERIFIER_VERSION", "stored-reference-verifier-v1").strip(),
        "CORS_ALLOWED_ORIGINS": origins,
        "CORS_ALLOW_CREDENTIALS": credentials,
        "API_TITLE": "MoMo-FDVS API",
        "API_VERSION": "v1",
        "OPENAPI_VERSION": "3.0.3",
        "OPENAPI_URL_PREFIX": "/api/v1",
        "OPENAPI_JSON_PATH": "openapi.json",
        "OPENAPI_SWAGGER_UI_PATH": None,
    }
