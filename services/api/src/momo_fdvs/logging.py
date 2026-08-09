"""Structured JSON logs, request correlation and sensitive-field redaction."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from flask import Flask, Response, g, has_request_context, request

SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "authorization",
        "cookie",
        "csrf_secret",
        "password",
        "refresh_token",
        "secret",
        "token",
    }
)


def redact(value: Any) -> Any:
    """Recursively replace values whose keys may contain credentials."""
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if str(key).lower() in SENSITIVE_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    """Emit one safe JSON object per application log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if has_request_context():
            payload["request_id"] = getattr(g, "request_id", None)
        context = getattr(record, "context", None)
        if context is not None:
            payload["context"] = redact(context)
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def configure_logging(app: Flask) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(app.config["LOG_LEVEL"])
    app.logger.propagate = False


def _request_id(raw: str | None) -> str:
    if raw:
        try:
            return str(UUID(raw))
        except (ValueError, AttributeError):
            pass
    return str(uuid4())


def register_request_hooks(app: Flask) -> None:
    @app.before_request
    def attach_request_context() -> None:
        g.request_id = _request_id(request.headers.get(app.config["REQUEST_ID_HEADER"]))
        g.request_started = time.perf_counter()

    @app.after_request
    def add_request_metadata(response: Response) -> Response:
        response.headers[app.config["REQUEST_ID_HEADER"]] = g.request_id
        duration_ms = round((time.perf_counter() - g.request_started) * 1000, 2)
        app.logger.info(
            "request_complete",
            extra={
                "context": {
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            },
        )
        return response

    @app.teardown_request
    def rollback_failed_unit_of_work(error: BaseException | None) -> None:
        if error is not None:
            from momo_fdvs.extensions import db

            db.session.rollback()
