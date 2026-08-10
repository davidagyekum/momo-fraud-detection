"""Authenticated receipt submission and private media delivery."""

from __future__ import annotations

import io
import uuid
from typing import Any, cast

from flask import Response, current_app, g, request, send_file
from flask.views import MethodView
from flask_smorest import Blueprint

from momo_fdvs.api.v1.transaction_schemas import TransactionUploadEnvelopeSchema
from momo_fdvs.errors import error_response
from momo_fdvs.extensions import db, limiter
from momo_fdvs.models import Transaction
from momo_fdvs.policies.auth import require_auth, require_roles
from momo_fdvs.services.audit import audit_event
from momo_fdvs.services.receipts import (
    ReceiptFailure,
    inspect_receipt,
    parse_client_captured_at,
    receipt_derivative,
    store_receipt,
    validate_client_metadata,
)
from momo_fdvs.storage.base import ObjectStorage

transactions_blueprint = Blueprint(
    "transactions-v1",
    __name__,
    url_prefix="/api/v1/transactions",
    description="Private transaction receipt evidence",
)


def _meta() -> dict[str, str]:
    return {"request_id": g.request_id}


def _storage() -> ObjectStorage:
    return cast(ObjectStorage, current_app.extensions["object_storage"])


def _audit_rejection(failure: ReceiptFailure) -> None:
    audit_event(
        "receipt.upload_rejected",
        "FAILURE",
        actor_id=g.current_user.id,
        roles=set(g.current_roles),
        target_type="transaction",
        metadata={"reason_code": failure.code, "http_status": failure.status},
    )
    db.session.commit()


def _upload_projection(result: Any) -> dict[str, Any]:
    receipt = result.receipt
    transaction = result.transaction
    base = f"/api/v1/transactions/{transaction.id}/receipt"
    quality_warnings = [
        warning for warning in receipt.quality_warnings if not str(warning).startswith("POSSIBLE_")
    ]
    return {
        "data": {
            "transaction": {
                "id": transaction.id,
                "status": transaction.status,
                "created_at": transaction.created_at,
            },
            "receipt": {
                "id": receipt.id,
                "media_type": receipt.media_type,
                "size_bytes": receipt.size_bytes,
                "width_px": receipt.width_px,
                "height_px": receipt.height_px,
                "quality_warnings": quality_warnings,
                "dimensions": {
                    "width_px": receipt.width_px,
                    "height_px": receipt.height_px,
                },
                "quality": {
                    "score": float(receipt.quality_score or 0),
                    "warnings": quality_warnings,
                },
                "duplicate_warning": result.duplicate_warning,
                "media": {
                    "thumbnail_url": f"{base}?variant=thumbnail",
                    "original_url": f"{base}?variant=original",
                },
            },
            "next_action": {
                "type": "RUN_OCR",
                "endpoint": f"/api/v1/transactions/{transaction.id}/ocr",
            },
            "replayed": result.replayed,
        },
        "meta": _meta(),
    }


@transactions_blueprint.route("")
class TransactionsResource(MethodView):
    @require_roles("USER")
    @limiter.limit(
        lambda: current_app.config["RATE_LIMIT_UPLOAD"],
        key_func=lambda: str(g.current_user.id),
    )
    @transactions_blueprint.doc(
        parameters=[
            {
                "in": "header",
                "name": "Idempotency-Key",
                "required": True,
                "schema": {"type": "string", "minLength": 8, "maxLength": 200},
            }
        ],
        requestBody={
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["receipt", "source"],
                        "properties": {
                            "receipt": {"type": "string", "format": "binary"},
                            "source": {"type": "string", "enum": ["CAMERA", "GALLERY"]},
                            "client_captured_at": {"type": "string", "format": "date-time"},
                            "client_metadata": {
                                "type": "string",
                                "description": "A size-limited JSON object of safe scalar values.",
                            },
                        },
                    }
                }
            },
        },
        responses={
            400: {"description": "Invalid image metadata or idempotency key."},
            401: {"description": "Authentication is required."},
            403: {"description": "The USER role is required."},
            409: {"description": "Idempotency conflict."},
            413: {"description": "Encoded bytes or decoded pixels exceed a limit."},
            415: {"description": "Unsupported, corrupt, disguised, or unsafe image."},
            429: {"description": "Per-user upload rate limit exceeded."},
            503: {"description": "Private storage is unavailable."},
        },
    )
    @transactions_blueprint.alt_response(
        200,
        schema=TransactionUploadEnvelopeSchema,
        description="A completed idempotent upload was replayed.",
    )
    @transactions_blueprint.response(201, TransactionUploadEnvelopeSchema)
    def post(self) -> Any:
        """Create a transaction from a strictly validated private receipt."""
        try:
            max_bytes = int(current_app.config["UPLOAD_MAX_BYTES"])
            if (
                request.content_length
                and request.content_length > current_app.config["UPLOAD_REQUEST_MAX_BYTES"]
            ):
                raise ReceiptFailure(
                    "RECEIPT_TOO_LARGE", f"The receipt must be {max_bytes} bytes or smaller.", 413
                )
            idempotency_key = request.headers.get("Idempotency-Key", "").strip()
            if not idempotency_key:
                raise ReceiptFailure(
                    "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key is required.", 400
                )
            upload = request.files.get("receipt")
            if upload is None:
                raise ReceiptFailure("RECEIPT_REQUIRED", "A receipt image is required.", 400)
            content = upload.stream.read(max_bytes + 1)
            inspected = inspect_receipt(content, upload.filename)
            captured_at = parse_client_captured_at(request.form.get("client_captured_at"))
            metadata = validate_client_metadata(request.form.get("client_metadata"))
            result = store_receipt(
                user=g.current_user,
                roles=set(g.current_roles),
                inspected=inspected,
                source=request.form.get("source", ""),
                captured_at=captured_at,
                client_metadata=metadata,
                idempotency_key=idempotency_key,
                storage=_storage(),
            )
            return _upload_projection(result), 200 if result.replayed else 201
        except ReceiptFailure as failure:
            db.session.rollback()
            _audit_rejection(failure)
            return error_response(failure.code, failure.message, failure.status)


@transactions_blueprint.route("/<uuid:transaction_id>/receipt")
class TransactionReceiptResource(MethodView):
    @require_auth
    @limiter.limit(
        lambda: current_app.config["RATE_LIMIT_RECEIPT_READ"],
        key_func=lambda: str(g.current_user.id),
    )
    @transactions_blueprint.doc(
        parameters=[
            {
                "in": "query",
                "name": "variant",
                "required": False,
                "schema": {
                    "type": "string",
                    "enum": ["thumbnail", "original"],
                    "default": "thumbnail",
                },
            }
        ],
        responses={
            200: {"description": "Private receipt image bytes."},
            404: {"description": "Receipt not found or not visible to the caller."},
            503: {"description": "Private storage is unavailable."},
        },
    )
    def get(self, transaction_id: uuid.UUID) -> Response | tuple[Response, int]:
        """Stream an owner-authorised original or derived thumbnail."""
        variant = request.args.get("variant", "thumbnail").lower()
        if variant not in {"thumbnail", "original"}:
            audit_event(
                "receipt.access_denied",
                "DENIED",
                actor_id=g.current_user.id,
                roles=set(g.current_roles),
                target_type="transaction",
                target_id=transaction_id,
                metadata={"reason_code": "RECEIPT_VARIANT_INVALID"},
            )
            db.session.commit()
            return error_response(
                "RECEIPT_VARIANT_INVALID", "Variant must be thumbnail or original.", 400
            )

        transaction = db.session.get(Transaction, transaction_id)
        staff_access = bool({"ADMIN", "INVESTIGATOR"} & set(g.current_roles))
        visible = transaction is not None and (
            transaction.user_id == g.current_user.id or staff_access
        )
        if not visible or transaction is None or transaction.receipt is None:
            audit_event(
                "receipt.access_denied",
                "DENIED",
                actor_id=g.current_user.id,
                roles=set(g.current_roles),
                target_type="transaction",
                target_id=transaction_id,
                metadata={"variant": variant},
            )
            db.session.commit()
            return error_response("RECEIPT_NOT_FOUND", "Receipt not found.", 404)

        receipt = transaction.receipt
        if variant == "thumbnail":
            derivative = receipt_derivative(receipt, "THUMBNAIL")
            if derivative is None:
                return error_response("RECEIPT_NOT_FOUND", "Receipt not found.", 404)
            object_key = derivative.object_key
            media_type = "image/jpeg"
            extension = "jpg"
        else:
            object_key = receipt.object_key
            media_type = receipt.media_type
            extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[media_type]

        try:
            content = _storage().read_bytes(object_key)
        except Exception as exc:
            current_app.logger.exception(
                "receipt_read_failed",
                exc_info=exc,
                extra={"transaction_id": str(transaction_id), "variant": variant},
            )
            audit_event(
                "receipt.access_failed",
                "FAILURE",
                actor_id=g.current_user.id,
                roles=set(g.current_roles),
                target_type="transaction",
                target_id=transaction_id,
                metadata={"variant": variant},
            )
            db.session.commit()
            return error_response(
                "RECEIPT_STORAGE_UNAVAILABLE",
                "The private receipt is temporarily unavailable.",
                503,
            )

        audit_event(
            "receipt.viewed",
            "SUCCESS",
            actor_id=g.current_user.id,
            roles=set(g.current_roles),
            target_type="transaction",
            target_id=transaction_id,
            metadata={"variant": variant, "staff_access": staff_access},
        )
        db.session.commit()
        response = send_file(
            io.BytesIO(content),
            mimetype=media_type,
            download_name=f"receipt-{receipt.id}.{extension}",
            as_attachment=False,
            max_age=0,
        )
        response.headers["Cache-Control"] = "private, no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "sandbox; default-src 'none'"
        return response


__all__ = ["transactions_blueprint"]
