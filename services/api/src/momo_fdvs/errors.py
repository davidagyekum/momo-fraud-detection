"""Standard public JSON error envelopes."""

from __future__ import annotations

from typing import Any

from flask import Flask, Response, g, jsonify
from werkzeug.exceptions import HTTPException

HTTP_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "AUTHENTICATION_REQUIRED",
    403: "PERMISSION_DENIED",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    503: "DEPENDENCY_UNAVAILABLE",
}


def error_response(
    code: str,
    message: str,
    status: int,
    field_errors: dict[str, list[str]] | None = None,
) -> tuple[Response, int]:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": getattr(g, "request_id", "unavailable"),
    }
    if field_errors:
        error["field_errors"] = field_errors
    return jsonify({"error": error}), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException) -> tuple[Response, int]:
        status = error.code or 500
        code = HTTP_ERROR_CODES.get(status, "HTTP_ERROR")
        if status < 500:
            message = error.description or "The request could not be completed."
        else:
            message = "The service could not complete the request."
        return error_response(code, message, status)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> tuple[Response, int]:
        app.logger.exception("unhandled_exception", exc_info=error)
        return error_response(
            "INTERNAL_SERVER_ERROR",
            "The service could not complete the request.",
            500,
        )
