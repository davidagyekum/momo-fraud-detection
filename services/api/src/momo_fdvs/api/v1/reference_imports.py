"""Private administrator reference-import and staff lookup routes."""

from __future__ import annotations

import io
import uuid
from typing import Any, cast

from flask import Response, current_app, g, request, send_file
from flask.views import MethodView
from flask_smorest import Blueprint
from sqlalchemy import func, or_, select

from momo_fdvs.api.v1.reference_schemas import (
    ReferenceCommitEnvelopeSchema,
    ReferenceImportEnvelopeSchema,
    ReferenceImportListEnvelopeSchema,
    ReferenceImportQuerySchema,
    ReferenceTransactionEnvelopeSchema,
    ReferenceTransactionListEnvelopeSchema,
    ReferenceTransactionQuerySchema,
    ReferenceValidationEnvelopeSchema,
)
from momo_fdvs.errors import error_response
from momo_fdvs.extensions import db, limiter
from momo_fdvs.models import ReferenceImportBatch, ReferenceTransaction
from momo_fdvs.policies.auth import require_roles
from momo_fdvs.services.audit import audit_event
from momo_fdvs.services.verification import (
    VerificationFailure,
    batch_projection,
    commit_reference_import,
    reference_projection,
    upload_reference_import,
    validate_reference_import,
)
from momo_fdvs.storage.base import ObjectStorage

reference_imports_blueprint = Blueprint(
    "reference-imports-v1",
    __name__,
    url_prefix="/api/v1/admin/reference-imports",
    description="Private stored-reference import workflow",
)
reference_transactions_blueprint = Blueprint(
    "reference-transactions-v1",
    __name__,
    url_prefix="/api/v1/admin/reference-transactions",
    description="Masked stored-reference lookup",
)


def _meta() -> dict[str, str]:
    return {"request_id": g.request_id}


def _storage() -> ObjectStorage:
    return cast(ObjectStorage, current_app.extensions["object_storage"])


def _failure(failure: VerificationFailure, target_id: uuid.UUID | None = None) -> Any:
    db.session.rollback()
    audit_event(
        "reference_import.request_rejected",
        "FAILURE",
        actor_id=g.current_user.id,
        roles=set(g.current_roles),
        target_type="reference_import_batch" if target_id else "reference_import",
        target_id=target_id,
        metadata={"reason_code": failure.code, "http_status": failure.status},
    )
    db.session.commit()
    return error_response(failure.code, failure.message, failure.status, failure.field_errors)


def _batch_or_none(batch_id: uuid.UUID) -> ReferenceImportBatch | None:
    return db.session.get(ReferenceImportBatch, batch_id)


@reference_imports_blueprint.route("")
class ReferenceImportsResource(MethodView):
    @require_roles("ADMIN")
    @reference_imports_blueprint.arguments(ReferenceImportQuerySchema, location="query")
    @reference_imports_blueprint.response(200, ReferenceImportListEnvelopeSchema)
    def get(self, query: dict[str, Any]) -> dict[str, Any]:
        statement = select(ReferenceImportBatch)
        count_statement = select(func.count(ReferenceImportBatch.id))
        if query.get("status"):
            statement = statement.where(ReferenceImportBatch.status == query["status"])
            count_statement = count_statement.where(ReferenceImportBatch.status == query["status"])
        if query.get("search"):
            pattern = f"%{query['search'].strip()}%"
            condition = or_(
                ReferenceImportBatch.source_label.ilike(pattern),
                ReferenceImportBatch.original_filename.ilike(pattern),
            )
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)
        page = query["page"]
        page_size = query["page_size"]
        imports = list(
            db.session.scalars(
                statement.order_by(ReferenceImportBatch.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return {
            "data": {
                "imports": [batch_projection(batch) for batch in imports],
                "page": page,
                "page_size": page_size,
                "total": db.session.scalar(count_statement) or 0,
            },
            "meta": _meta(),
        }

    @require_roles("ADMIN")
    @limiter.limit(
        lambda: current_app.config["RATE_LIMIT_REFERENCE_IMPORT"],
        key_func=lambda: str(g.current_user.id),
    )
    @reference_imports_blueprint.doc(
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
                        "required": ["file", "source_label"],
                        "properties": {
                            "file": {"type": "string", "format": "binary"},
                            "source_label": {"type": "string", "maxLength": 200},
                        },
                    }
                }
            },
        },
    )
    @reference_imports_blueprint.alt_response(
        200,
        schema=ReferenceImportEnvelopeSchema,
        description="A completed upload or duplicate file was replayed.",
    )
    @reference_imports_blueprint.response(201, ReferenceImportEnvelopeSchema)
    def post(self) -> Any:
        try:
            key = request.headers.get("Idempotency-Key", "").strip()
            if not key:
                raise VerificationFailure(
                    "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key is required.", 400
                )
            upload = request.files.get("file")
            if upload is None:
                raise VerificationFailure("REFERENCE_FILE_REQUIRED", "A CSV file is required.", 400)
            maximum = int(current_app.config["REFERENCE_IMPORT_MAX_BYTES"])
            result = upload_reference_import(
                user=g.current_user,
                roles=set(g.current_roles),
                source_label=request.form.get("source_label", ""),
                filename=upload.filename,
                content=upload.stream.read(maximum + 1),
                idempotency_key=key,
                storage=_storage(),
            )
            return (
                {"data": batch_projection(result.batch), "meta": _meta()},
                200 if result.replayed else 201,
            )
        except VerificationFailure as failure:
            return _failure(failure)


@reference_imports_blueprint.route("/<uuid:batch_id>")
class ReferenceImportResource(MethodView):
    @require_roles("ADMIN")
    @reference_imports_blueprint.response(200, ReferenceImportEnvelopeSchema)
    def get(self, batch_id: uuid.UUID) -> Any:
        batch = _batch_or_none(batch_id)
        if batch is None:
            return error_response("REFERENCE_IMPORT_NOT_FOUND", "Import not found.", 404)
        return {"data": batch_projection(batch), "meta": _meta()}


@reference_imports_blueprint.route("/<uuid:batch_id>/validate")
class ReferenceImportValidationResource(MethodView):
    @require_roles("ADMIN")
    @limiter.limit(
        lambda: current_app.config["RATE_LIMIT_REFERENCE_IMPORT"],
        key_func=lambda: str(g.current_user.id),
    )
    @reference_imports_blueprint.response(200, ReferenceValidationEnvelopeSchema)
    def post(self, batch_id: uuid.UUID) -> Any:
        batch = _batch_or_none(batch_id)
        if batch is None:
            return error_response("REFERENCE_IMPORT_NOT_FOUND", "Import not found.", 404)
        try:
            result = validate_reference_import(
                batch=batch,
                user=g.current_user,
                roles=set(g.current_roles),
                storage=_storage(),
            )
            limit = int(current_app.config["REFERENCE_IMPORT_PREVIEW_ERRORS"])
            return {
                "data": {
                    "batch": batch_projection(batch),
                    "batch_id": batch.id,
                    "status": batch.status,
                    "total_rows": batch.total_rows,
                    "valid_rows": batch.valid_rows,
                    "invalid_rows": batch.invalid_rows,
                    "invalid_rows_download": batch_projection(batch)["invalid_rows_download"],
                    "errors": result.errors[:limit],
                    "preview_truncated": len(result.errors) > limit,
                },
                "meta": _meta(),
            }
        except VerificationFailure as failure:
            return _failure(failure, batch_id)


@reference_imports_blueprint.route("/<uuid:batch_id>/commit")
class ReferenceImportCommitResource(MethodView):
    @require_roles("ADMIN")
    @limiter.limit(
        lambda: current_app.config["RATE_LIMIT_REFERENCE_IMPORT"],
        key_func=lambda: str(g.current_user.id),
    )
    @reference_imports_blueprint.doc(
        parameters=[
            {
                "in": "header",
                "name": "Idempotency-Key",
                "required": True,
                "schema": {"type": "string", "minLength": 8, "maxLength": 200},
            }
        ]
    )
    @reference_imports_blueprint.response(200, ReferenceCommitEnvelopeSchema)
    def post(self, batch_id: uuid.UUID) -> Any:
        batch = _batch_or_none(batch_id)
        if batch is None:
            return error_response("REFERENCE_IMPORT_NOT_FOUND", "Import not found.", 404)
        try:
            key = request.headers.get("Idempotency-Key", "").strip()
            if not key:
                raise VerificationFailure(
                    "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key is required.", 400
                )
            committed, replayed = commit_reference_import(
                batch=batch,
                user=g.current_user,
                roles=set(g.current_roles),
                idempotency_key=key,
                storage=_storage(),
            )
            return {
                "data": {
                    "batch": batch_projection(batch),
                    "committed_rows": committed,
                    "replayed": replayed,
                },
                "meta": _meta(),
            }
        except VerificationFailure as failure:
            return _failure(failure, batch_id)


@reference_imports_blueprint.route("/<uuid:batch_id>/invalid-rows")
class ReferenceImportInvalidRowsResource(MethodView):
    @require_roles("ADMIN")
    def get(self, batch_id: uuid.UUID) -> Response | tuple[Response, int]:
        batch = _batch_or_none(batch_id)
        if batch is None or not batch.invalid_report_key:
            return error_response("INVALID_ROWS_NOT_FOUND", "Invalid-row report not found.", 404)
        try:
            content = _storage().read_bytes(batch.invalid_report_key)
        except (OSError, ValueError):
            return error_response(
                "INVALID_ROWS_UNAVAILABLE", "The invalid-row report is unavailable.", 503
            )
        audit_event(
            "reference_import.invalid_rows_downloaded",
            "SUCCESS",
            actor_id=g.current_user.id,
            roles=set(g.current_roles),
            target_type="reference_import_batch",
            target_id=batch.id,
        )
        db.session.commit()
        response = send_file(
            io.BytesIO(content),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"reference-import-{batch.id}-invalid-rows.csv",
            max_age=0,
        )
        response.headers["Cache-Control"] = "private, no-store, max-age=0"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "sandbox; default-src 'none'"
        return response


@reference_transactions_blueprint.route("")
class ReferenceTransactionsResource(MethodView):
    @require_roles("ADMIN", "INVESTIGATOR")
    @reference_transactions_blueprint.arguments(ReferenceTransactionQuerySchema, location="query")
    @reference_transactions_blueprint.response(200, ReferenceTransactionListEnvelopeSchema)
    def get(self, query: dict[str, Any]) -> dict[str, Any]:
        statement = select(ReferenceTransaction).join(ReferenceImportBatch)
        count_statement = select(func.count(ReferenceTransaction.id)).join(ReferenceImportBatch)
        conditions = [ReferenceImportBatch.status == "COMMITTED"]
        if query.get("provider_code"):
            conditions.append(
                ReferenceTransaction.provider_code == query["provider_code"].strip().upper()
            )
        if query.get("search"):
            pattern = f"%{query['search'].strip()}%"
            conditions.append(ReferenceTransaction.transaction_reference.ilike(pattern))
        statement = statement.where(*conditions)
        count_statement = count_statement.where(*conditions)
        page = query["page"]
        page_size = query["page_size"]
        references = list(
            db.session.scalars(
                statement.order_by(ReferenceTransaction.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return {
            "data": {
                "references": [reference_projection(item) for item in references],
                "page": page,
                "page_size": page_size,
                "total": db.session.scalar(count_statement) or 0,
            },
            "meta": _meta(),
        }


@reference_transactions_blueprint.route("/<uuid:reference_id>")
class ReferenceTransactionResource(MethodView):
    @require_roles("ADMIN", "INVESTIGATOR")
    @reference_transactions_blueprint.response(200, ReferenceTransactionEnvelopeSchema)
    def get(self, reference_id: uuid.UUID) -> Any:
        reference = db.session.get(ReferenceTransaction, reference_id)
        if reference is None or reference.import_batch.status != "COMMITTED":
            return error_response("REFERENCE_TRANSACTION_NOT_FOUND", "Reference not found.", 404)
        audit_event(
            "reference_transaction.viewed",
            "SUCCESS",
            actor_id=g.current_user.id,
            roles=set(g.current_roles),
            target_type="reference_transaction",
            target_id=reference.id,
        )
        db.session.commit()
        return {"data": reference_projection(reference), "meta": _meta()}


__all__ = ["reference_imports_blueprint", "reference_transactions_blueprint"]
