"""Owner/staff projections of persisted immutable analysis evidence."""

from __future__ import annotations

import uuid
from typing import Any

from flask import current_app, g
from flask.views import MethodView
from flask_smorest import Blueprint
from sqlalchemy import select

from momo_fdvs.api.v1.analysis_schemas import (
    AnalysisEnvelopeSchema,
    AnalysisEvidenceEnvelopeSchema,
)
from momo_fdvs.errors import error_response
from momo_fdvs.extensions import db, limiter
from momo_fdvs.models import (
    AnalysisRun,
    AnalysisStageRun,
    ImageAnalysis,
    Transaction,
    VerificationResult,
)
from momo_fdvs.policies.auth import require_auth
from momo_fdvs.services.audit import audit_event
from momo_fdvs.services.image_forensics import (
    image_evidence_projection,
    unavailable_image_evidence,
)
from momo_fdvs.services.verification import verification_projection

analyses_blueprint = Blueprint(
    "analyses-v1",
    __name__,
    url_prefix="/api/v1/analyses",
    description="Persisted immutable analysis results and evidence",
)


def _meta() -> dict[str, str]:
    return {"request_id": g.request_id}


def _as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _visible_analysis(
    analysis_run_id: uuid.UUID,
) -> tuple[AnalysisRun, Transaction, bool] | None:
    staff_access = bool({"ADMIN", "INVESTIGATOR"} & set(g.current_roles))
    statement = (
        select(AnalysisRun, Transaction)
        .join(Transaction, Transaction.id == AnalysisRun.transaction_id)
        .where(AnalysisRun.id == analysis_run_id)
    )
    if not staff_access:
        statement = statement.where(Transaction.user_id == g.current_user.id)
    row = db.session.execute(statement).one_or_none()
    if row is None:
        return None
    return row.AnalysisRun, row.Transaction, staff_access


def _analysis_rows(
    run: AnalysisRun,
) -> tuple[VerificationResult | None, ImageAnalysis | None, list[AnalysisStageRun]]:
    verification = db.session.scalar(
        select(VerificationResult).where(VerificationResult.analysis_run_id == run.id)
    )
    image_analysis = db.session.scalar(
        select(ImageAnalysis).where(ImageAnalysis.analysis_run_id == run.id)
    )
    stages = list(
        db.session.scalars(
            select(AnalysisStageRun)
            .where(AnalysisStageRun.analysis_run_id == run.id)
            .order_by(AnalysisStageRun.created_at, AnalysisStageRun.stage)
        ).all()
    )
    return verification, image_analysis, stages


def risk_projection(run: AnalysisRun) -> dict[str, Any]:
    policy = _as_dict(run.component_scores.get("policy"))
    reasons = policy.get("reasons", run.top_reasons)
    if not isinstance(reasons, list):
        reasons = []
    missing_signals = policy.get("missing_signals", [])
    limitations = policy.get("limitations", [])
    return {
        "status": str(policy.get("status", "UNAVAILABLE")),
        "band": str(policy.get("band", "inconclusive")),
        "class": policy.get("legacy_risk_class", run.risk_class),
        "score": policy.get("score"),
        "summary": str(
            policy.get(
                "summary",
                "The available evidence is insufficient for a fraud-risk conclusion.",
            )
        ),
        "reasons": reasons,
        "missing_signals": missing_signals if isinstance(missing_signals, list) else [],
        "limitations": limitations if isinstance(limitations, list) else [],
        "policy_version": str(
            policy.get(
                "policy_version",
                run.configuration_snapshot.get("policy_version", "unavailable"),
            )
        ),
    }


def _stage_projection(stage: AnalysisStageRun) -> dict[str, Any]:
    return {
        "stage": stage.stage,
        "status": stage.status,
        "attempt": stage.attempt,
        "duration_ms": stage.duration_ms,
        "error_code": stage.error_code,
    }


def _versions_projection(run: AnalysisRun) -> dict[str, Any]:
    snapshot = run.configuration_snapshot
    return {
        "policy_version": snapshot.get("policy_version"),
        "policy_sha256": snapshot.get("policy_sha256"),
        "rule_set_version": snapshot.get("rule_set_version"),
        "ocr_pipeline_version": snapshot.get("ocr_pipeline_version"),
        "ocr_engine_version": snapshot.get("ocr_engine_version"),
        "image_forensics_version": snapshot.get("image_forensics_version"),
        "image_model_version": snapshot.get("image_model_version"),
        "structured_model_version": snapshot.get("structured_model_version"),
    }


def _component_projection(value: object) -> dict[str, Any]:
    component = _as_dict(value)
    result: dict[str, Any] = {
        "status": str(component.get("status", "UNAVAILABLE")),
        "reason_code": component.get("reason_code"),
    }
    reason_codes = component.get("reason_codes")
    if isinstance(reason_codes, list):
        result["reason_codes"] = reason_codes
    result["model_version"] = component.get("version")
    return result


def _analysis_projection(
    run: AnalysisRun,
    transaction: Transaction,
    verification: VerificationResult | None,
    stages: list[AnalysisStageRun],
) -> dict[str, Any]:
    components = run.component_scores
    stage_items = [_stage_projection(stage) for stage in stages]
    completed = sum(stage.status in {"COMPLETED", "SKIPPED", "FAILED"} for stage in stages)
    return {
        "id": run.id,
        "transaction_id": transaction.id,
        "status": run.status,
        "risk": risk_projection(run),
        "verification": (
            verification_projection(verification) if verification is not None else None
        ),
        "evidence_summary": {
            "deterministic_image": _component_projection(components.get("deterministic_image")),
            "image_model": _component_projection(components.get("image_model")),
            "structured_model": _component_projection(components.get("structured_model")),
            "automated_evidence_immutable": True,
        },
        "versions": _versions_projection(run),
        "progress": {
            "current_stage": run.current_stage,
            "completed_stage_count": completed,
            "total_stage_count": len(stages),
            "stages": stage_items,
        },
        "evidence_url": f"/api/v1/analyses/{run.id}/evidence",
        "created_at": run.created_at,
        "completed_at": run.completed_at,
    }


def _deny(analysis_run_id: uuid.UUID, action: str) -> Any:
    audit_event(
        action,
        "DENIED",
        actor_id=g.current_user.id,
        roles=set(g.current_roles),
        target_type="analysis_run",
        target_id=analysis_run_id,
    )
    db.session.commit()
    return error_response("ANALYSIS_NOT_FOUND", "Analysis not found.", 404)


@analyses_blueprint.route("/<uuid:analysis_run_id>")
class AnalysisResource(MethodView):
    @require_auth
    @limiter.limit(
        lambda: current_app.config["RATE_LIMIT_RECEIPT_READ"],
        key_func=lambda: str(g.current_user.id),
    )
    @analyses_blueprint.doc(
        responses={
            401: {"description": "Authentication is required."},
            404: {"description": "Analysis is not visible to the caller."},
        }
    )
    @analyses_blueprint.response(200, AnalysisEnvelopeSchema)
    def get(self, analysis_run_id: uuid.UUID) -> Any:
        """Return the persisted policy result and bounded progress projection."""
        visible = _visible_analysis(analysis_run_id)
        if visible is None:
            return _deny(analysis_run_id, "analysis.result_access_denied")
        run, transaction, staff_access = visible
        verification, _image_analysis, stages = _analysis_rows(run)
        audit_event(
            "analysis.result_viewed",
            "SUCCESS",
            actor_id=g.current_user.id,
            roles=set(g.current_roles),
            target_type="analysis_run",
            target_id=run.id,
            metadata={"staff_access": staff_access},
        )
        db.session.commit()
        return {
            "data": _analysis_projection(run, transaction, verification, stages),
            "meta": _meta(),
        }


@analyses_blueprint.route("/<uuid:analysis_run_id>/evidence")
class AnalysisEvidenceResource(MethodView):
    @require_auth
    @limiter.limit(
        lambda: current_app.config["RATE_LIMIT_RECEIPT_READ"],
        key_func=lambda: str(g.current_user.id),
    )
    @analyses_blueprint.doc(
        responses={
            401: {"description": "Authentication is required."},
            404: {"description": "Analysis evidence is not visible to the caller."},
        }
    )
    @analyses_blueprint.response(200, AnalysisEvidenceEnvelopeSchema)
    def get(self, analysis_run_id: uuid.UUID) -> Any:
        """Return owner-safe evidence and staff-only diagnostic links."""
        visible = _visible_analysis(analysis_run_id)
        if visible is None:
            return _deny(analysis_run_id, "analysis.evidence_access_denied")
        run, transaction, staff_access = visible
        verification, image_analysis, stages = _analysis_rows(run)
        deterministic_stage = next(
            (stage for stage in stages if stage.stage == "DETERMINISTIC_IMAGE"), None
        )
        audit_event(
            "analysis.evidence_viewed",
            "SUCCESS",
            actor_id=g.current_user.id,
            roles=set(g.current_roles),
            target_type="analysis_run",
            target_id=analysis_run_id,
            metadata={
                "staff_access": staff_access,
                "diagnostic_links_included": staff_access,
            },
        )
        db.session.commit()
        return {
            "data": {
                "analysis_run_id": run.id,
                "transaction_id": transaction.id,
                "status": run.status,
                "current_stage": run.current_stage,
                "automated_evidence_immutable": True,
                "risk": risk_projection(run),
                "verification": (
                    verification_projection(verification) if verification is not None else None
                ),
                "image_evidence": (
                    image_evidence_projection(
                        image_analysis,
                        transaction_id=transaction.id,
                        include_diagnostics=staff_access,
                    )
                    if image_analysis is not None
                    else unavailable_image_evidence(
                        deterministic_stage.error_code
                        if deterministic_stage is not None and deterministic_stage.error_code
                        else "IMAGE_ANALYSIS_UNAVAILABLE"
                    )
                ),
                "stages": [_stage_projection(stage) for stage in stages],
                "configuration_versions": _versions_projection(run),
            },
            "meta": _meta(),
        }


__all__ = ["analyses_blueprint", "risk_projection"]
