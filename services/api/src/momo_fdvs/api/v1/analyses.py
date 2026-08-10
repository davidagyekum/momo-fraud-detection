"""Owner/staff projections of immutable automated analysis evidence."""

from __future__ import annotations

import uuid
from typing import Any

from flask import current_app, g
from flask.views import MethodView
from flask_smorest import Blueprint
from sqlalchemy import select

from momo_fdvs.api.v1.analysis_schemas import AnalysisEvidenceEnvelopeSchema
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
    description="Immutable automated analysis evidence",
)


def _meta() -> dict[str, str]:
    return {"request_id": g.request_id}


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
        run = db.session.get(AnalysisRun, analysis_run_id)
        transaction = db.session.get(Transaction, run.transaction_id) if run is not None else None
        staff_access = bool({"ADMIN", "INVESTIGATOR"} & set(g.current_roles))
        visible = transaction is not None and (
            transaction.user_id == g.current_user.id or staff_access
        )
        if run is None or transaction is None or not visible:
            audit_event(
                "analysis.evidence_access_denied",
                "DENIED",
                actor_id=g.current_user.id,
                roles=set(g.current_roles),
                target_type="analysis_run",
                target_id=analysis_run_id,
            )
            db.session.commit()
            return error_response("ANALYSIS_NOT_FOUND", "Analysis not found.", 404)
        verification = db.session.scalar(
            select(VerificationResult).where(VerificationResult.analysis_run_id == analysis_run_id)
        )
        image_analysis = db.session.scalar(
            select(ImageAnalysis).where(ImageAnalysis.analysis_run_id == analysis_run_id)
        )
        stages = list(
            db.session.scalars(
                select(AnalysisStageRun)
                .where(AnalysisStageRun.analysis_run_id == analysis_run_id)
                .order_by(AnalysisStageRun.created_at, AnalysisStageRun.stage)
            ).all()
        )
        image_stage = next((stage for stage in stages if stage.stage == "IMAGE_ANALYSIS"), None)
        audit_event(
            "analysis.evidence_viewed",
            "SUCCESS",
            actor_id=g.current_user.id,
            roles=set(g.current_roles),
            target_type="analysis_run",
            target_id=analysis_run_id,
            metadata={"staff_access": staff_access, "diagnostic_links_included": staff_access},
        )
        db.session.commit()
        return {
            "data": {
                "analysis_run_id": run.id,
                "transaction_id": transaction.id,
                "status": run.status,
                "current_stage": run.current_stage,
                "automated_evidence_immutable": True,
                "risk": {
                    "status": "UNAVAILABLE",
                    "class": None,
                    "score": None,
                    "reason_code": "MODEL_AND_RISK_STAGES_NOT_AVAILABLE",
                    "summary": "Fraud risk has not been calculated in this build.",
                },
                "verification": verification_projection(verification)
                if verification is not None
                else None,
                "image_evidence": image_evidence_projection(
                    image_analysis,
                    transaction_id=transaction.id,
                    include_diagnostics=staff_access,
                )
                if image_analysis is not None
                else unavailable_image_evidence(
                    image_stage.error_code
                    if image_stage is not None and image_stage.error_code
                    else "IMAGE_ANALYSIS_UNAVAILABLE"
                ),
                "stages": [
                    {
                        "stage": stage.stage,
                        "status": stage.status,
                        "attempt": stage.attempt,
                        "duration_ms": stage.duration_ms,
                        "error_code": stage.error_code,
                    }
                    for stage in stages
                ],
                "configuration_versions": {
                    "verifier_version": run.configuration_snapshot.get("verifier_version"),
                    "rule_set_version": run.configuration_snapshot.get("rule_set_version"),
                    "image_forensics_version": run.configuration_snapshot.get(
                        "image_forensics_version"
                    ),
                    "image_feature_schema_version": run.configuration_snapshot.get(
                        "image_feature_schema_version"
                    ),
                },
            },
            "meta": _meta(),
        }


__all__ = ["analyses_blueprint"]
