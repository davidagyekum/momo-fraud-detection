"""Private owner analysis-report generation and download."""

from __future__ import annotations

import hashlib
import io
import uuid
from typing import Any, cast

from flask import Response, current_app, g, request, send_file
from flask.views import MethodView
from flask_smorest import Blueprint

from momo_fdvs.api.v1.report_schemas import AnalysisReportCreateSchema, ReportEnvelopeSchema
from momo_fdvs.errors import error_response
from momo_fdvs.extensions import db, limiter
from momo_fdvs.policies.auth import require_roles
from momo_fdvs.services.audit import audit_event
from momo_fdvs.services.reports import (
    ReportFailure,
    create_analysis_report,
    create_case_report,
    owned_ready_report,
    report_projection,
    staff_ready_case_report,
)
from momo_fdvs.storage.base import ObjectStorage

reports_blueprint = Blueprint(
    "reports-v1",
    __name__,
    url_prefix="/api/v1",
    description="Private immutable analysis reports",
)


def _meta() -> dict[str, str]:
    return {"request_id": g.request_id}


def _storage() -> ObjectStorage:
    return cast(ObjectStorage, current_app.extensions["object_storage"])


@reports_blueprint.route("/transactions/<uuid:transaction_id>/reports")
class AnalysisReportCreateResource(MethodView):
    @require_roles("USER")
    @limiter.limit(
        lambda: current_app.config["RATE_LIMIT_UPLOAD"],
        key_func=lambda: str(g.current_user.id),
    )
    @reports_blueprint.arguments(AnalysisReportCreateSchema)
    @reports_blueprint.response(201, ReportEnvelopeSchema)
    @reports_blueprint.alt_response(200, schema=ReportEnvelopeSchema)
    def post(self, payload: dict[str, Any], transaction_id: uuid.UUID) -> Any:
        """Generate or replay an owner-scoped immutable analysis report."""
        idempotency_key = request.headers.get("Idempotency-Key", "").strip()
        if not idempotency_key:
            return error_response(
                "IDEMPOTENCY_KEY_REQUIRED",
                "Idempotency-Key is required for report generation.",
                400,
            )
        try:
            result = create_analysis_report(
                user=g.current_user,
                roles=set(g.current_roles),
                transaction_id=transaction_id,
                idempotency_key=idempotency_key,
                report_format=str(payload["format"]),
                storage=_storage(),
            )
        except ReportFailure as failure:
            return error_response(failure.code, failure.message, failure.status)
        body = {
            "data": report_projection(result.artifact, replayed=result.replayed),
            "meta": _meta(),
        }
        return body, 200 if result.replayed else 201


@reports_blueprint.route("/reports/<uuid:report_id>/download")
class AnalysisReportDownloadResource(MethodView):
    @require_roles("USER")
    @limiter.limit(
        lambda: current_app.config["RATE_LIMIT_RECEIPT_READ"],
        key_func=lambda: str(g.current_user.id),
    )
    def get(self, report_id: uuid.UUID) -> Response | tuple[Response, int]:
        """Download an owned ready report with integrity and privacy controls."""
        artifact = owned_ready_report(g.current_user.id, report_id)
        if artifact is None:
            return error_response("REPORT_NOT_FOUND", "Report not found.", 404)
        try:
            content = _storage().read_bytes(artifact.object_key)
        except Exception as exc:
            current_app.logger.exception("analysis_report_read_failed", exc_info=exc)
            audit_event(
                "report.download_failed",
                "FAILURE",
                actor_id=g.current_user.id,
                roles=set(g.current_roles),
                target_type="report_artifact",
                target_id=artifact.id,
            )
            db.session.commit()
            return error_response(
                "REPORT_STORAGE_UNAVAILABLE",
                "The report is temporarily unavailable.",
                503,
            )
        if artifact.sha256 is None or hashlib.sha256(content).hexdigest() != artifact.sha256:
            current_app.logger.error(
                "analysis_report_integrity_failed", extra={"report_id": str(artifact.id)}
            )
            return error_response(
                "REPORT_INTEGRITY_FAILED",
                "The report is temporarily unavailable.",
                503,
            )
        audit_event(
            "report.downloaded",
            "SUCCESS",
            actor_id=g.current_user.id,
            roles=set(g.current_roles),
            target_type="report_artifact",
            target_id=artifact.id,
        )
        db.session.commit()
        response = send_file(
            io.BytesIO(content),
            mimetype="text/html",
            as_attachment=True,
            download_name=f"momo-analysis-{artifact.id}.html",
            max_age=0,
        )
        response.headers["Cache-Control"] = "private, no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "sandbox; default-src 'none'"
        return response


@reports_blueprint.route("/admin/cases/<uuid:case_id>/reports")
class CaseReportCreateResource(MethodView):
    @require_roles("ADMIN", "INVESTIGATOR")
    @reports_blueprint.arguments(AnalysisReportCreateSchema)
    @reports_blueprint.response(201, ReportEnvelopeSchema)
    @reports_blueprint.alt_response(200, schema=ReportEnvelopeSchema)
    def post(self, payload: dict[str, Any], case_id: uuid.UUID) -> Any:
        """Generate or replay a version-bound staff case report."""
        if payload["format"] != "HTML":
            return error_response(
                "REPORT_FORMAT_UNSUPPORTED", "Only HTML reports are supported.", 400
            )
        key = request.headers.get("Idempotency-Key", "").strip()
        if not key:
            return error_response(
                "IDEMPOTENCY_KEY_REQUIRED",
                "Idempotency-Key is required for report generation.",
                400,
            )
        try:
            result = create_case_report(
                case_id=case_id,
                user=g.current_user,
                roles=set(g.current_roles),
                idempotency_key=key,
                storage=_storage(),
            )
        except ReportFailure as failure:
            return error_response(failure.code, failure.message, failure.status)
        body = {
            "data": report_projection(result.artifact, replayed=result.replayed),
            "meta": _meta(),
        }
        return body, 200 if result.replayed else 201


@reports_blueprint.route("/admin/cases/<uuid:case_id>/reports/<uuid:report_id>/download")
class CaseReportDownloadResource(MethodView):
    @require_roles("ADMIN", "INVESTIGATOR")
    def get(self, case_id: uuid.UUID, report_id: uuid.UUID) -> Response | tuple[Response, int]:
        """Download a ready case report without exposing its object key."""
        artifact = staff_ready_case_report(case_id, report_id)
        if artifact is None:
            return error_response("REPORT_NOT_FOUND", "Report not found.", 404)
        try:
            content = _storage().read_bytes(artifact.object_key)
        except Exception as exc:
            current_app.logger.exception("case_report_read_failed", exc_info=exc)
            return error_response(
                "REPORT_STORAGE_UNAVAILABLE", "The report is temporarily unavailable.", 503
            )
        if artifact.sha256 is None or hashlib.sha256(content).hexdigest() != artifact.sha256:
            return error_response(
                "REPORT_INTEGRITY_FAILED", "The report is temporarily unavailable.", 503
            )
        audit_event(
            "case.report_downloaded",
            "SUCCESS",
            actor_id=g.current_user.id,
            roles=set(g.current_roles),
            target_type="report_artifact",
            target_id=artifact.id,
            metadata={"case_id": str(case_id), "case_version": artifact.source_version},
        )
        db.session.commit()
        response = send_file(
            io.BytesIO(content),
            mimetype="text/html",
            as_attachment=True,
            download_name=f"momo-case-{case_id}.html",
            max_age=0,
        )
        response.headers["Cache-Control"] = "private, no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "sandbox; default-src 'none'"
        return response


__all__ = ["reports_blueprint"]
