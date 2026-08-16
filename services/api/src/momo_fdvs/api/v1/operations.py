"""Bounded masked staff operations and readiness endpoints."""

from __future__ import annotations

import math
import uuid
from collections import Counter
from typing import Any

from flask import g
from flask.views import MethodView
from flask_smorest import Blueprint
from sqlalchemy import func, select

from momo_fdvs.api.v1.operations_schemas import (
    AuditQuerySchema,
    OperationalDataEnvelopeSchema,
    PageQuerySchema,
    TransactionQuerySchema,
)
from momo_fdvs.errors import error_response
from momo_fdvs.extensions import db
from momo_fdvs.models import (
    AnalysisRun,
    AnalysisStageRun,
    AuditLog,
    FraudCase,
    FraudRule,
    FraudRuleSet,
    ModelVersion,
    OCRConfirmation,
    ReportArtifact,
    Transaction,
    VerificationResult,
)
from momo_fdvs.policies.auth import require_roles
from momo_fdvs.readiness import probe_readiness
from momo_fdvs.services.audit import audit_event

operations_blueprint = Blueprint(
    "operations-v1",
    __name__,
    url_prefix="/api/v1/admin",
    description="Masked staff operational views",
)


def _meta() -> dict[str, str]:
    return {"request_id": g.request_id}


def _audit(action: str, target_type: str, target_id: uuid.UUID | None = None) -> None:
    audit_event(
        action,
        "SUCCESS",
        actor_id=g.current_user.id,
        roles=set(g.current_roles),
        target_type=target_type,
        target_id=target_id,
    )


def _policy_band(run: AnalysisRun | None) -> str:
    if run is None or not isinstance(run.component_scores, dict):
        return "not_analysed"
    policy = run.component_scores.get("policy")
    return str(policy.get("band", "inconclusive")) if isinstance(policy, dict) else "inconclusive"


def _verification_status(run_id: uuid.UUID | None) -> str | None:
    if run_id is None:
        return None
    return db.session.scalar(
        select(VerificationResult.status).where(VerificationResult.analysis_run_id == run_id)
    )


def _transaction_projection(transaction: Transaction) -> dict[str, Any]:
    run = (
        db.session.get(AnalysisRun, transaction.latest_analysis_run_id)
        if transaction.latest_analysis_run_id is not None
        else None
    )
    active_case = db.session.scalar(
        select(FraudCase)
        .where(FraudCase.transaction_id == transaction.id)
        .order_by(FraudCase.opened_at.desc())
        .limit(1)
    )
    return {
        "id": transaction.id,
        "provider_code": transaction.provider_code,
        "display_reference_masked": transaction.display_reference_masked,
        "status": transaction.status,
        "created_at": transaction.created_at,
        "updated_at": transaction.updated_at,
        "analysis": (
            {
                "id": run.id,
                "status": run.status,
                "risk_band": _policy_band(run),
                "verification_status": _verification_status(run.id),
                "completed_at": run.completed_at,
            }
            if run is not None
            else None
        ),
        "case": (
            {"id": active_case.id, "status": active_case.status, "source": active_case.source}
            if active_case is not None
            else None
        ),
    }


@operations_blueprint.route("/dashboard")
class DashboardResource(MethodView):
    @require_roles("ADMIN", "INVESTIGATOR")
    @operations_blueprint.response(200, OperationalDataEnvelopeSchema)
    def get(self) -> dict[str, Any]:
        """Return independent bounded operational aggregates."""
        runs = list(db.session.scalars(select(AnalysisRun)).all())
        risk_counts = Counter(_policy_band(run) for run in runs)
        analysis_counts = Counter(run.status for run in runs)
        verification_counts = Counter(db.session.scalars(select(VerificationResult.status)).all())
        case_status_counts = Counter(db.session.scalars(select(FraudCase.status)).all())
        case_source_counts = Counter(db.session.scalars(select(FraudCase.source)).all())
        durations = sorted(
            int(value)
            for value in db.session.scalars(
                select(func.sum(AnalysisStageRun.duration_ms))
                .where(AnalysisStageRun.duration_ms.is_not(None))
                .group_by(AnalysisStageRun.analysis_run_id)
            ).all()
            if value is not None
        )
        recent = list(
            db.session.scalars(
                select(AuditLog).order_by(AuditLog.created_at.desc()).limit(10)
            ).all()
        )
        active_models = list(
            db.session.scalars(select(ModelVersion).where(ModelVersion.status == "ACTIVE")).all()
        )
        active_rules = db.session.scalar(
            select(FraudRuleSet).where(FraudRuleSet.status == "ACTIVE")
        )
        _audit("operations.dashboard_viewed", "operations_dashboard")
        db.session.commit()
        return {
            "data": {
                "risk_counts": dict(risk_counts),
                "verification_counts": dict(verification_counts),
                "case_status_counts": dict(case_status_counts),
                "case_source_counts": dict(case_source_counts),
                "analysis_status_counts": dict(analysis_counts),
                "processing_duration_ms": {
                    "average": round(sum(durations) / len(durations)) if durations else None,
                    "p95": durations[min(math.ceil(len(durations) * 0.95) - 1, len(durations) - 1)]
                    if durations
                    else None,
                },
                "active_versions": {
                    "models": [
                        {"type": model.model_type, "name": model.name, "version": model.version}
                        for model in active_models
                    ],
                    "rule_set": active_rules.version if active_rules is not None else None,
                },
                "recent_activity": [
                    {
                        "id": item.id,
                        "action": item.action,
                        "outcome": item.outcome,
                        "target_type": item.target_type,
                        "created_at": item.created_at,
                    }
                    for item in recent
                ],
            },
            "meta": _meta(),
        }


@operations_blueprint.route("/transactions")
class AdminTransactionsResource(MethodView):
    @require_roles("ADMIN", "INVESTIGATOR")
    @operations_blueprint.arguments(TransactionQuerySchema, location="query")
    @operations_blueprint.response(200, OperationalDataEnvelopeSchema)
    def get(self, query: dict[str, Any]) -> dict[str, Any]:
        conditions = []
        if query.get("status"):
            conditions.append(Transaction.status == query["status"].strip().upper())
        if query.get("provider"):
            conditions.append(Transaction.provider_code == query["provider"].strip().upper())
        total = (
            db.session.scalar(select(func.count()).select_from(Transaction).where(*conditions)) or 0
        )
        page, page_size = query["page"], query["page_size"]
        rows = list(
            db.session.scalars(
                select(Transaction)
                .where(*conditions)
                .order_by(Transaction.created_at.desc(), Transaction.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        _audit("operations.transactions_viewed", "transaction")
        db.session.commit()
        return {
            "data": {
                "items": [_transaction_projection(item) for item in rows],
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": math.ceil(total / page_size),
            },
            "meta": _meta(),
        }


@operations_blueprint.route("/transactions/<uuid:transaction_id>")
class AdminTransactionResource(MethodView):
    @require_roles("ADMIN", "INVESTIGATOR")
    @operations_blueprint.response(200, OperationalDataEnvelopeSchema)
    def get(self, transaction_id: uuid.UUID) -> Any:
        transaction = db.session.get(Transaction, transaction_id)
        if transaction is None:
            return error_response("TRANSACTION_NOT_FOUND", "Transaction not found.", 404)
        confirmation_count = (
            db.session.scalar(
                select(func.count())
                .select_from(OCRConfirmation)
                .where(OCRConfirmation.transaction_id == transaction.id)
            )
            or 0
        )
        projection = {
            **_transaction_projection(transaction),
            "receipt_available": transaction.receipt is not None,
            "ocr_confirmation_count": confirmation_count,
            "automated_evidence_immutable": True,
        }
        _audit("operations.transaction_viewed", "transaction", transaction.id)
        db.session.commit()
        return {"data": projection, "meta": _meta()}


@operations_blueprint.route("/audit-logs")
class AuditLogResource(MethodView):
    @require_roles("ADMIN")
    @operations_blueprint.arguments(AuditQuerySchema, location="query")
    @operations_blueprint.response(200, OperationalDataEnvelopeSchema)
    def get(self, query: dict[str, Any]) -> dict[str, Any]:
        conditions = []
        if query.get("action"):
            conditions.append(AuditLog.action == query["action"].strip())
        if query.get("outcome"):
            conditions.append(AuditLog.outcome == query["outcome"])
        total = (
            db.session.scalar(select(func.count()).select_from(AuditLog).where(*conditions)) or 0
        )
        page, page_size = query["page"], query["page_size"]
        rows = list(
            db.session.scalars(
                select(AuditLog)
                .where(*conditions)
                .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        _audit("operations.audit_log_viewed", "audit_log")
        db.session.commit()
        return {
            "data": {
                "items": [
                    {
                        "id": item.id,
                        "action": item.action,
                        "outcome": item.outcome,
                        "target_type": item.target_type,
                        "actor_roles": item.actor_role_snapshot,
                        "created_at": item.created_at,
                    }
                    for item in rows
                ],
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": math.ceil(total / page_size),
            },
            "meta": _meta(),
        }


@operations_blueprint.route("/reports")
class StaffReportsResource(MethodView):
    @require_roles("ADMIN", "INVESTIGATOR")
    @operations_blueprint.arguments(PageQuerySchema, location="query")
    @operations_blueprint.response(200, OperationalDataEnvelopeSchema)
    def get(self, query: dict[str, Any]) -> dict[str, Any]:
        condition = ReportArtifact.report_type == "CASE"
        total = (
            db.session.scalar(select(func.count()).select_from(ReportArtifact).where(condition))
            or 0
        )
        page, page_size = query["page"], query["page_size"]
        rows = list(
            db.session.scalars(
                select(ReportArtifact)
                .where(condition)
                .order_by(ReportArtifact.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        _audit("operations.reports_viewed", "report_artifact")
        db.session.commit()
        return {
            "data": {
                "items": [
                    {
                        "id": item.id,
                        "report_type": item.report_type,
                        "case_id": item.case_id,
                        "source_version": item.source_version,
                        "status": item.status,
                        "sha256": item.sha256,
                        "generated_at": item.generated_at,
                        "download_url": (
                            f"/api/v1/admin/cases/{item.case_id}/reports/{item.id}/download"
                            if item.status == "READY" and item.case_id is not None
                            else None
                        ),
                    }
                    for item in rows
                ],
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": math.ceil(total / page_size),
            },
            "meta": _meta(),
        }


@operations_blueprint.route("/system-status")
class SystemStatusResource(MethodView):
    @require_roles("ADMIN")
    @operations_blueprint.response(200, OperationalDataEnvelopeSchema)
    def get(self) -> dict[str, Any]:
        readiness = probe_readiness().as_dict()
        active = Counter(
            db.session.scalars(
                select(ModelVersion.model_type).where(ModelVersion.status == "ACTIVE")
            ).all()
        )
        readiness["components"]["image_model"] = {
            "status": "ready" if active["IMAGE"] else "degraded",
            **({} if active["IMAGE"] else {"reason": "not_activated"}),
        }
        readiness["components"]["structured_model"] = {
            "status": "ready" if active["STRUCTURED"] else "degraded",
            **({} if active["STRUCTURED"] else {"reason": "not_activated"}),
        }
        readiness["components"]["notification_adapter"] = {
            "status": "disabled",
            "reason": "external_delivery_not_configured",
        }
        _audit("operations.system_status_viewed", "system_status")
        db.session.commit()
        return {"data": readiness, "meta": _meta()}


@operations_blueprint.route("/models")
class ModelRegistryResource(MethodView):
    @require_roles("ADMIN")
    @operations_blueprint.arguments(PageQuerySchema, location="query")
    @operations_blueprint.response(200, OperationalDataEnvelopeSchema)
    def get(self, query: dict[str, Any]) -> dict[str, Any]:
        page, page_size = query["page"], query["page_size"]
        total = db.session.scalar(select(func.count()).select_from(ModelVersion)) or 0
        rows = list(
            db.session.scalars(
                select(ModelVersion)
                .order_by(ModelVersion.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        _audit("operations.models_viewed", "model_version")
        db.session.commit()
        return {
            "data": {
                "items": [
                    {
                        "id": item.id,
                        "model_type": item.model_type,
                        "name": item.name,
                        "version": item.version,
                        "status": item.status,
                        "preprocessing_version": item.preprocessing_version,
                        "created_at": item.created_at,
                    }
                    for item in rows
                ],
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": math.ceil(total / page_size),
            },
            "meta": _meta(),
        }


@operations_blueprint.route("/models/<uuid:model_id>")
class ModelRegistryDetailResource(MethodView):
    @require_roles("ADMIN")
    @operations_blueprint.response(200, OperationalDataEnvelopeSchema)
    def get(self, model_id: uuid.UUID) -> Any:
        item = db.session.get(ModelVersion, model_id)
        if item is None:
            return error_response("MODEL_NOT_FOUND", "Model not found.", 404)
        _audit("operations.model_viewed", "model_version", item.id)
        db.session.commit()
        return {
            "data": {
                "id": item.id,
                "model_type": item.model_type,
                "name": item.name,
                "version": item.version,
                "status": item.status,
                "preprocessing_version": item.preprocessing_version,
                "framework_versions": item.framework_versions,
                "metrics": item.metrics,
                "dataset_manifest_hash": item.dataset_manifest_hash,
                "split_hash": item.split_hash,
                "training_commit_sha": item.training_commit_sha,
                "created_at": item.created_at,
            },
            "meta": _meta(),
        }


@operations_blueprint.route("/rule-sets")
class RuleSetResource(MethodView):
    @require_roles("ADMIN")
    @operations_blueprint.arguments(PageQuerySchema, location="query")
    @operations_blueprint.response(200, OperationalDataEnvelopeSchema)
    def get(self, query: dict[str, Any]) -> dict[str, Any]:
        page, page_size = query["page"], query["page_size"]
        total = db.session.scalar(select(func.count()).select_from(FraudRuleSet)) or 0
        rows = list(
            db.session.scalars(
                select(FraudRuleSet)
                .order_by(FraudRuleSet.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        counts: dict[uuid.UUID, int] = {
            rule_set_id: count
            for rule_set_id, count in db.session.execute(
                select(FraudRule.rule_set_id, func.count(FraudRule.id)).group_by(
                    FraudRule.rule_set_id
                )
            ).all()
        }
        _audit("operations.rule_sets_viewed", "fraud_rule_set")
        db.session.commit()
        return {
            "data": {
                "items": [
                    {
                        "id": item.id,
                        "version": item.version,
                        "status": item.status,
                        "description": item.description,
                        "row_version": item.row_version,
                        "rule_count": counts.get(item.id, 0),
                        "created_at": item.created_at,
                    }
                    for item in rows
                ],
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": math.ceil(total / page_size),
            },
            "meta": _meta(),
        }


@operations_blueprint.route("/rule-sets/<uuid:rule_set_id>")
class RuleSetDetailResource(MethodView):
    @require_roles("ADMIN")
    @operations_blueprint.response(200, OperationalDataEnvelopeSchema)
    def get(self, rule_set_id: uuid.UUID) -> Any:
        item = db.session.get(FraudRuleSet, rule_set_id)
        if item is None:
            return error_response("RULE_SET_NOT_FOUND", "Rule set not found.", 404)
        rules = list(
            db.session.scalars(
                select(FraudRule).where(FraudRule.rule_set_id == item.id).order_by(FraudRule.code)
            ).all()
        )
        _audit("operations.rule_set_viewed", "fraud_rule_set", item.id)
        db.session.commit()
        return {
            "data": {
                "id": item.id,
                "version": item.version,
                "status": item.status,
                "description": item.description,
                "row_version": item.row_version,
                "created_at": item.created_at,
                "rules": [
                    {
                        "id": rule.id,
                        "code": rule.code,
                        "description": rule.description,
                        "severity": rule.severity,
                        "score_contribution": float(rule.score_contribution),
                        "enabled": rule.enabled,
                    }
                    for rule in rules
                ],
            },
            "meta": _meta(),
        }


__all__ = ["operations_blueprint"]
