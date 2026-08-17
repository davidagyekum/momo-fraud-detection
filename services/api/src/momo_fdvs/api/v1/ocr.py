"""Owner-only OCR run, review, confirmation and analysis-readiness routes."""

from __future__ import annotations

import uuid
from typing import Any

from flask import current_app, g, request
from flask.views import MethodView
from flask_smorest import Blueprint

from momo_fdvs.api.v1.ocr_schemas import (
    AnalysisStartEnvelopeSchema,
    AnalysisStartRequestSchema,
    OCRConfirmationEnvelopeSchema,
    OCRConfirmationRequestSchema,
    OCRReviewEnvelopeSchema,
)
from momo_fdvs.errors import error_response
from momo_fdvs.extensions import db, limiter
from momo_fdvs.models import OCRResult
from momo_fdvs.policies.auth import owned_transaction, require_roles
from momo_fdvs.services.analysis_orchestrator import (
    AnalysisEvidenceSelection,
    AnalysisFailure,
    run_analysis,
)
from momo_fdvs.services.audit import audit_event
from momo_fdvs.services.ocr import (
    OCRFailure,
    confirm_ocr,
    latest_confirmation,
    latest_ocr_result,
    run_and_store_ocr,
)
from momo_fdvs.services.text_fraud import stored_text_assessment_projection
from momo_fdvs.storage.base import ObjectStorage

ocr_blueprint = Blueprint(
    "ocr-v1",
    __name__,
    url_prefix="/api/v1/transactions",
    description="Private OCR evidence and owner correction workflow",
)


def _meta() -> dict[str, str]:
    return {"request_id": g.request_id}


def _storage() -> ObjectStorage:
    return current_app.extensions["object_storage"]  # type: ignore[no-any-return]


def _failure(failure: OCRFailure, transaction_id: uuid.UUID) -> Any:
    db.session.rollback()
    audit_event(
        "ocr.request_rejected",
        "FAILURE",
        actor_id=g.current_user.id,
        roles=set(g.current_roles),
        target_type="transaction",
        target_id=transaction_id,
        metadata={"reason_code": failure.code, "http_status": failure.status},
    )
    db.session.commit()
    return error_response(failure.code, failure.message, failure.status, failure.field_errors)


def _field_projection(value: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "raw_value",
        "value",
        "confidence",
        "valid",
        "requires_review",
        "source_token_ids",
        "warnings",
        "currency",
        "masked",
    }
    return {key: item for key, item in value.items() if key in allowed}


def _review_projection(
    transaction_id: uuid.UUID, ocr_result: OCRResult, *, replayed: bool = False
) -> dict[str, Any]:
    fields = {
        name: _field_projection(value)
        for name, value in ocr_result.extracted_fields.items()
        if name != "provider_code" and not name.startswith("_") and isinstance(value, dict)
    }
    provider_field = ocr_result.extracted_fields.get("provider_code", {})
    provider = {
        "value": provider_field.get("value") or "GENERIC_MOMO",
        "confidence": float(provider_field.get("confidence", 0)),
        "requires_review": bool(provider_field.get("requires_review", True)),
        "warnings": list(provider_field.get("warnings", [])),
    }
    fraud_preview = stored_text_assessment_projection(
        ocr_result.extracted_fields.get("_text_fraud")
    )
    partial = bool(
        {
            "OCR_ENGINE_UNAVAILABLE",
            "OCR_ENGINE_TIMEOUT",
            "OCR_ENGINE_FAILED",
            "CRITICAL_OCR_FIELDS_MISSING",
        }
        & set(ocr_result.warnings)
    )
    return {
        "data": {
            "transaction_id": transaction_id,
            "status": "OCR_PARTIAL" if partial else "OCR_READY",
            "ocr_result_id": ocr_result.id,
            "provider": provider,
            "fraud_preview": fraud_preview,
            "fields": fields,
            "warnings": list(ocr_result.warnings),
            "raw_text": ocr_result.raw_text,
            "selected_variant": ocr_result.selected_variant,
            "pipeline_version": ocr_result.pipeline_version,
            "engine_version": ocr_result.engine_version,
            "preview_url": f"/api/v1/transactions/{transaction_id}/receipt?variant=thumbnail",
            "confirmation_endpoint": f"/api/v1/transactions/{transaction_id}/ocr-confirmations",
            "replayed": replayed,
        },
        "meta": _meta(),
    }


@ocr_blueprint.route("/<uuid:transaction_id>/ocr")
class OCRRunResource(MethodView):
    @require_roles("USER")
    @limiter.limit(
        lambda: current_app.config["RATE_LIMIT_OCR"],
        key_func=lambda: str(g.current_user.id),
    )
    @ocr_blueprint.doc(
        parameters=[
            {
                "in": "header",
                "name": "Idempotency-Key",
                "required": True,
                "schema": {"type": "string", "minLength": 8, "maxLength": 200},
            }
        ],
        responses={
            400: {"description": "Missing or invalid idempotency key."},
            401: {"description": "Authentication is required."},
            403: {"description": "The USER role is required."},
            404: {"description": "Transaction not found."},
            409: {"description": "Invalid state, idempotency conflict or hash mismatch."},
            429: {"description": "Per-user OCR rate limit exceeded."},
            503: {"description": "Private storage or OCR processing is unavailable."},
        },
    )
    @ocr_blueprint.response(200, OCRReviewEnvelopeSchema)
    def post(self, transaction_id: uuid.UUID) -> Any:
        """Run a bounded, reconstructable OCR pipeline for an owned receipt."""
        transaction = owned_transaction(transaction_id)
        if transaction is None:
            return error_response("TRANSACTION_NOT_FOUND", "Transaction not found.", 404)
        try:
            key = request.headers.get("Idempotency-Key", "").strip()
            if not key:
                raise OCRFailure("IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key is required.", 400)
            result = run_and_store_ocr(
                transaction=transaction,
                user=g.current_user,
                roles=set(g.current_roles),
                idempotency_key=key,
                storage=_storage(),
            )
            return _review_projection(transaction_id, result.ocr_result, replayed=result.replayed)
        except OCRFailure as failure:
            return _failure(failure, transaction_id)


@ocr_blueprint.route("/<uuid:transaction_id>/ocr-review")
class OCRReviewResource(MethodView):
    @require_roles("USER")
    @limiter.limit(
        lambda: current_app.config["RATE_LIMIT_OCR_REVIEW"],
        key_func=lambda: str(g.current_user.id),
    )
    @ocr_blueprint.doc(
        responses={
            401: {"description": "Authentication is required."},
            403: {"description": "The USER role is required."},
            404: {"description": "Transaction not found."},
            409: {"description": "OCR has not been run."},
        }
    )
    @ocr_blueprint.response(200, OCRReviewEnvelopeSchema)
    def get(self, transaction_id: uuid.UUID) -> Any:
        """Return the latest owner-safe OCR projection without raw token boxes."""
        transaction = owned_transaction(transaction_id)
        if transaction is None:
            return error_response("TRANSACTION_NOT_FOUND", "Transaction not found.", 404)
        result = latest_ocr_result(transaction)
        if result is None:
            return error_response("OCR_NOT_RUN", "Run OCR before opening the review screen.", 409)
        return _review_projection(transaction_id, result)


@ocr_blueprint.route("/<uuid:transaction_id>/ocr-confirmations")
class OCRConfirmationResource(MethodView):
    @require_roles("USER")
    @limiter.limit(
        lambda: current_app.config["RATE_LIMIT_OCR_REVIEW"],
        key_func=lambda: str(g.current_user.id),
    )
    @ocr_blueprint.doc(
        parameters=[
            {
                "in": "header",
                "name": "Idempotency-Key",
                "required": True,
                "schema": {"type": "string", "minLength": 8, "maxLength": 200},
            }
        ],
        responses={
            400: {"description": "Missing or invalid idempotency key."},
            404: {"description": "Transaction or OCR result not found."},
            409: {"description": "Invalid review state or idempotency conflict."},
            422: {"description": "Canonical field or correction-reason validation failed."},
        },
    )
    @ocr_blueprint.arguments(OCRConfirmationRequestSchema)
    @ocr_blueprint.alt_response(
        200,
        schema=OCRConfirmationEnvelopeSchema,
        description="A completed idempotent confirmation was replayed.",
    )
    @ocr_blueprint.response(201, OCRConfirmationEnvelopeSchema)
    def post(self, payload: dict[str, Any], transaction_id: uuid.UUID) -> Any:
        """Create an immutable canonical snapshot and correction audit."""
        transaction = owned_transaction(transaction_id)
        if transaction is None:
            return error_response("TRANSACTION_NOT_FOUND", "Transaction not found.", 404)
        result_id = payload["ocr_result_id"]
        ocr_result = db.session.get(OCRResult, result_id)
        if (
            ocr_result is None
            or transaction.receipt is None
            or ocr_result.receipt_id != transaction.receipt.id
        ):
            return error_response("OCR_RESULT_NOT_FOUND", "OCR result not found.", 404)
        try:
            key = request.headers.get("Idempotency-Key", "").strip()
            if not key:
                raise OCRFailure("IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key is required.", 400)
            result = confirm_ocr(
                transaction=transaction,
                ocr_result=ocr_result,
                user=g.current_user,
                roles=set(g.current_roles),
                raw_fields=payload["confirmed_fields"],
                correction_reasons=payload.get("correction_reasons", {}),
                idempotency_key=key,
            )
            confirmation = result.confirmation
            response = {
                "data": {
                    "confirmation_id": confirmation.id,
                    "ocr_result_id": confirmation.ocr_result_id,
                    "transaction_id": transaction.id,
                    "status": "OCR_REVIEWED",
                    "schema_version": confirmation.schema_version,
                    "corrected_fields": [item["field"] for item in confirmation.corrections],
                    "replayed": result.replayed,
                    "next_action": {
                        "type": "RUN_ANALYSIS",
                        "endpoint": f"/api/v1/transactions/{transaction.id}/analyses",
                    },
                },
                "meta": _meta(),
            }
            return response, 200 if result.replayed else 201
        except OCRFailure as failure:
            return _failure(failure, transaction_id)


@ocr_blueprint.route("/<uuid:transaction_id>/analyses")
class AnalysisReadinessResource(MethodView):
    @require_roles("USER")
    @limiter.limit(
        lambda: current_app.config["RATE_LIMIT_OCR_REVIEW"],
        key_func=lambda: str(g.current_user.id),
    )
    @ocr_blueprint.doc(
        parameters=[
            {
                "in": "header",
                "name": "Idempotency-Key",
                "required": True,
                "schema": {"type": "string", "minLength": 8, "maxLength": 200},
            }
        ],
        responses={
            409: {"description": "OCR review is required before analysis."},
            503: {"description": "Stored verification configuration is unavailable."},
        },
    )
    @ocr_blueprint.arguments(AnalysisStartRequestSchema, required=False)
    @ocr_blueprint.response(202, AnalysisStartEnvelopeSchema)
    def post(self, payload: dict[str, Any], transaction_id: uuid.UUID) -> Any:
        """Run combined analysis or an OCR-result-only screenshot analysis."""
        transaction = owned_transaction(transaction_id)
        if transaction is None:
            return error_response("TRANSACTION_NOT_FOUND", "Transaction not found.", 404)
        try:
            mode = payload.get("mode", "combined")
            if mode == "screenshot_only":
                raw_ocr_result_id = payload.get("ocr_result_id")
                if raw_ocr_result_id is None:
                    raise AnalysisFailure(
                        "OCR_RESULT_REQUIRED",
                        "An OCR result is required for screenshot-only analysis.",
                        422,
                    )
                ocr_result_id = raw_ocr_result_id
                ocr_result = db.session.get(OCRResult, ocr_result_id)
                if (
                    ocr_result is None
                    or transaction.receipt is None
                    or ocr_result.receipt_id != transaction.receipt.id
                ):
                    raise AnalysisFailure("OCR_RESULT_NOT_FOUND", "OCR result not found.", 404)
                evidence = AnalysisEvidenceSelection.screenshot_only(ocr_result)
            else:
                if payload.get("ocr_result_id") is not None:
                    raise AnalysisFailure(
                        "ANALYSIS_REQUEST_INVALID", "The analysis request is invalid.", 422
                    )
                confirmation = latest_confirmation(transaction)
                if (
                    transaction.status not in {"READY", "PARTIAL", "COMPLETED"}
                    or confirmation is None
                ):
                    raise AnalysisFailure(
                        "OCR_REVIEW_REQUIRED",
                        "Confirm the OCR fields before starting combined analysis.",
                        409,
                    )
                evidence = AnalysisEvidenceSelection.combined(confirmation)
            key = request.headers.get("Idempotency-Key", "").strip()
            if not key:
                raise AnalysisFailure(
                    "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key is required.", 400
                )
            result = run_analysis(
                transaction=transaction,
                user=g.current_user,
                roles=set(g.current_roles),
                idempotency_key=key,
                storage=_storage(),
                evidence=evidence,
            )
            return {
                "data": {
                    "analysis_run_id": result.run.id,
                    "transaction_id": transaction.id,
                    "status": result.run.status,
                    "current_stage": result.run.current_stage,
                    "poll_url": f"/api/v1/analyses/{result.run.id}",
                    "replayed": result.replayed,
                },
                "meta": _meta(),
            }
        except AnalysisFailure as failure:
            db.session.rollback()
            audit_event(
                "analysis.request_rejected",
                "FAILURE",
                actor_id=g.current_user.id,
                roles=set(g.current_roles),
                target_type="transaction",
                target_id=transaction.id,
                metadata={"reason_code": failure.code, "http_status": failure.status},
            )
            db.session.commit()
            return error_response(failure.code, failure.message, failure.status)


__all__ = ["ocr_blueprint"]
