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
    OCRConfirmation,
    Transaction,
    VerificationResult,
)
from momo_fdvs.policies.auth import require_auth
from momo_fdvs.policies.evidence_access import transaction_evidence_access
from momo_fdvs.services.audit import audit_event
from momo_fdvs.services.image_forensics import (
    image_evidence_projection,
    unavailable_image_evidence,
)
from momo_fdvs.services.risk_policy import derive_finalization_semantics
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
    statement = (
        select(AnalysisRun, Transaction)
        .join(Transaction, Transaction.id == AnalysisRun.transaction_id)
        .where(AnalysisRun.id == analysis_run_id)
    )
    row = db.session.execute(statement).one_or_none()
    if row is None:
        return None
    visible, staff_access = transaction_evidence_access(
        row.Transaction,
        user_id=g.current_user.id,
        roles=set(g.current_roles),
    )
    if not visible:
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
    band = str(policy.get("band", "inconclusive"))
    semantics = derive_finalization_semantics(
        analysis_status=run.status,
        risk_band=band,
        missing_signals=tuple(str(value) for value in missing_signals if isinstance(value, str))
        if isinstance(missing_signals, list)
        else (),
    )
    return {
        "status": str(policy.get("status", "UNAVAILABLE")),
        "band": band,
        "conclusion_status": semantics.conclusion_status,
        "component_status": semantics.component_status,
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
        "disclaimer": ("This is an automated risk assessment, not a final legal determination."),
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
        "text_fraud_schema_version": snapshot.get("text_fraud_schema_version"),
        "text_fraud_ruleset_version": snapshot.get("text_fraud_ruleset_version"),
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


def _text_fraud_projection(value: object) -> dict[str, Any]:
    component = _as_dict(value)
    reason_codes = component.get("reason_codes")
    limitations = component.get("limitations")
    return {
        "status": str(component.get("status", "UNAVAILABLE")),
        "class": component.get("class"),
        "policy_score": component.get("score"),
        "score_is_probability": False,
        "reason_codes": reason_codes if isinstance(reason_codes, list) else [],
        "evidence_quality": str(component.get("evidence_quality", "UNAVAILABLE")),
        "ruleset_version": component.get("ruleset_version"),
        "limitations": limitations if isinstance(limitations, list) else [],
    }


def _analysis_projection(
    run: AnalysisRun,
    transaction: Transaction,
    verification: VerificationResult | None,
    stages: list[AnalysisStageRun],
) -> dict[str, Any]:
    components = run.component_scores
    stage_items = [_stage_projection(stage) for stage in stages]
    completed = sum(stage.status in {"COMPLETED", "SKIPPED", "FAILED"} for stage in stages)
    confirmation = (
        db.session.get(OCRConfirmation, run.ocr_confirmation_id)
        if run.ocr_confirmation_id is not None
        else None
    )
    ocr_result_id = (
        run.ocr_result_id
        if run.ocr_result_id is not None
        else confirmation.ocr_result_id
        if confirmation is not None
        else None
    )
    if ocr_result_id is None:
        raise RuntimeError("analysis run is missing its immutable OCR evidence")
    return {
        "id": run.id,
        "transaction_id": transaction.id,
        "analysis_mode": run.analysis_mode,
        "ocr_result_id": ocr_result_id,
        "ocr_confirmation_id": run.ocr_confirmation_id,
        "status": run.status,
        "risk": risk_projection(run),
        "verification": (
            verification_projection(verification) if verification is not None else None
        ),
        "evidence_summary": {
            "deterministic_image": _component_projection(components.get("deterministic_image")),
            "image_model": _component_projection(components.get("image_model")),
            "structured_model": _component_projection(components.get("structured_model")),
            "text_fraud": _text_fraud_projection(components.get("text_fraud")),
            "automated_evidence_immutable": True,
        },
        "ocr_review": {
            "status": "CONFIRMED" if confirmation is not None else "NOT_REQUIRED",
            "ocr_result_id": ocr_result_id,
            "confirmed_field_count": (
                len(confirmation.confirmed_fields) if confirmation is not None else 0
            ),
            "correction_count": len(confirmation.corrections) if confirmation is not None else 0,
            "schema_version": confirmation.schema_version if confirmation is not None else None,
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
        confirmation = (
            db.session.get(OCRConfirmation, run.ocr_confirmation_id)
            if run.ocr_confirmation_id is not None
            else None
        )
        ocr_result_id = (
            run.ocr_result_id
            if run.ocr_result_id is not None
            else confirmation.ocr_result_id
            if confirmation is not None
            else None
        )
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
                "analysis_mode": run.analysis_mode,
                "ocr_result_id": ocr_result_id,
                "ocr_confirmation_id": run.ocr_confirmation_id,
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
