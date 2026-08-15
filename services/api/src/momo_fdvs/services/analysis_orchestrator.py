"""Bounded synchronous orchestration for immutable receipt analysis evidence."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from flask import current_app
from sqlalchemy import select

from momo_fdvs.contracts.evidence import (
    EvidenceMode,
    canonical_image_from_legacy,
)
from momo_fdvs.extensions import db
from momo_fdvs.models import (
    AnalysisRun,
    AnalysisStageRun,
    FraudPrediction,
    FraudRuleSet,
    ImageAnalysis,
    ModelVersion,
    OCRConfirmation,
    Transaction,
    User,
    VerificationResult,
)
from momo_fdvs.services.audit import audit_event
from momo_fdvs.services.image_forensics import ImageForensicsFailure, run_image_forensics
from momo_fdvs.services.image_model import ImageModelFailure, predict_image_tampering
from momo_fdvs.services.risk_policy import (
    AnalysisPolicyInput,
    ModelPolicySignal,
    PolicyFailure,
    PolicyReason,
    evaluate_risk_policy,
    load_risk_policy,
)
from momo_fdvs.services.verification import (
    VerificationFailure,
    claim_idempotency,
    evaluate_verification,
    request_hash,
    verification_reuse_warnings,
)
from momo_fdvs.storage.base import ObjectStorage

ANALYSIS_STAGES = (
    "SNAPSHOT",
    "VERIFICATION",
    "DETERMINISTIC_IMAGE",
    "IMAGE_MODEL",
    "STRUCTURED_MODEL",
    "SEMANTIC_RULES",
    "RISK_POLICY",
    "FINALIZE",
)
_POLICY_PATH = Path(__file__).resolve().parents[1] / "policies" / "risk_policy_demo_v1.json"
_SEVERITIES = {"INFORMATIONAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"}


class AnalysisFailure(RuntimeError):
    """A public-safe orchestration failure."""

    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


@dataclass(frozen=True)
class AnalysisOrchestrationResult:
    run: AnalysisRun
    verification: VerificationResult
    image_analysis: ImageAnalysis | None
    stages: tuple[AnalysisStageRun, ...]
    replayed: bool


def _stage_start(run: AnalysisRun, stage: str) -> tuple[datetime, float]:
    run.current_stage = stage
    return datetime.now(UTC), time.perf_counter()


def _record_stage(
    run: AnalysisRun,
    stage: str,
    started_at: datetime,
    started_counter: float,
    *,
    status: str,
    error_code: str | None = None,
    details: dict[str, Any] | None = None,
) -> AnalysisStageRun:
    completed_at = datetime.now(UTC)
    result = AnalysisStageRun(
        analysis_run_id=run.id,
        stage=stage,
        status=status,
        attempt=1,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=max(0, round((time.perf_counter() - started_counter) * 1000)),
        error_code=error_code,
        details=details or {},
    )
    db.session.add(result)
    return result


def _ordered_stages(run_id: Any) -> tuple[AnalysisStageRun, ...]:
    rows = list(
        db.session.scalars(
            select(AnalysisStageRun).where(AnalysisStageRun.analysis_run_id == run_id)
        ).all()
    )
    by_name = {row.stage: row for row in rows}
    return tuple(by_name[name] for name in ANALYSIS_STAGES if name in by_name)


def _active_model(model_type: str) -> ModelVersion | None:
    return db.session.scalar(
        select(ModelVersion)
        .where(ModelVersion.model_type == model_type, ModelVersion.status == "ACTIVE")
        .order_by(ModelVersion.activated_at.desc().nullslast(), ModelVersion.created_at.desc())
    )


def _numeric_prediction_value(
    prediction: dict[str, object], key: str, *, integer: bool = False
) -> float | int:
    value = prediction.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ImageModelFailure(
            "IMAGE_MODEL_OUTPUT_INVALID",
            "The active image model returned an invalid output.",
        )
    return int(value) if integer else float(value)


def _model_projection(signal: ModelPolicySignal) -> dict[str, Any]:
    return {
        "status": "SUCCESS" if signal.available else "UNAVAILABLE",
        "score": signal.score,
        "class": signal.predicted_class,
        "reason_codes": list(signal.reason_codes),
        "version": signal.model_version,
        "artifact_sha256": signal.artifact_sha256,
        "schema_hash": signal.schema_hash,
    }


def _deterministic_reasons(result: ImageAnalysis | None) -> tuple[PolicyReason, ...]:
    if result is None:
        return ()
    domains = (
        result.metadata_evidence,
        result.duplicate_evidence,
        result.compression_evidence,
        result.noise_evidence,
        result.layout_evidence,
        result.quality_evidence,
    )
    reasons: dict[str, PolicyReason] = {}
    for domain in domains:
        for signal in domain.get("signals", []):
            if signal.get("status") != "TRIGGERED":
                continue
            code = str(signal.get("code", ""))
            title = str(signal.get("reason", "")).strip()
            severity = str(signal.get("severity", "INFORMATIONAL"))
            if code and title and severity in _SEVERITIES:
                reasons.setdefault(
                    code,
                    PolicyReason(
                        code=code,
                        title=title,
                        severity=cast(Any, severity),
                    ),
                )
    return tuple(reasons.values())


def _corrected_low_confidence_fields(
    confirmation: OCRConfirmation,
) -> tuple[str, ...]:
    corrected = {
        str(item.get("field"))
        for item in confirmation.corrections
        if isinstance(item, dict) and item.get("field")
    }
    threshold = float(current_app.config["OCR_REVIEW_CONFIDENCE_THRESHOLD"])
    low: list[str] = []
    for field in ("amount", "transaction_reference"):
        if field not in corrected:
            continue
        raw_confidence = confirmation.ocr_result.field_confidences.get(field)
        if isinstance(raw_confidence, dict):
            raw_confidence = raw_confidence.get("confidence")
        if isinstance(raw_confidence, (int, float)) and float(raw_confidence) < threshold:
            low.append(field)
    return tuple(low)


def _replay_result(
    record_resource_id: Any,
    transaction: Transaction,
) -> AnalysisOrchestrationResult:
    run = db.session.get(AnalysisRun, record_resource_id)
    if run is None or run.transaction_id != transaction.id:
        raise AnalysisFailure(
            "IDEMPOTENCY_RESOURCE_UNAVAILABLE",
            "The original analysis is unavailable.",
            409,
        )
    verification = db.session.scalar(
        select(VerificationResult).where(VerificationResult.analysis_run_id == run.id)
    )
    if verification is None:
        raise AnalysisFailure(
            "IDEMPOTENCY_RESOURCE_UNAVAILABLE",
            "The original analysis is unavailable.",
            409,
        )
    image_analysis = db.session.scalar(
        select(ImageAnalysis).where(ImageAnalysis.analysis_run_id == run.id)
    )
    return AnalysisOrchestrationResult(
        run=run,
        verification=verification,
        image_analysis=image_analysis,
        stages=_ordered_stages(run.id),
        replayed=True,
    )


def run_analysis(
    *,
    transaction: Transaction,
    confirmation: OCRConfirmation,
    user: User,
    roles: set[str],
    idempotency_key: str,
    storage: ObjectStorage,
    policy_path: Path | None = None,
    mode: EvidenceMode = EvidenceMode.SCREENSHOT_ONLY,
) -> AnalysisOrchestrationResult:
    """Execute one bounded analysis and atomically persist its final projection."""

    try:
        policy = load_risk_policy(policy_path or _POLICY_PATH)
    except PolicyFailure as failure:
        raise AnalysisFailure(failure.code, failure.message, 503) from None
    rule_set = db.session.scalar(
        select(FraudRuleSet)
        .where(FraudRuleSet.status == "ACTIVE")
        .order_by(FraudRuleSet.activated_at.desc().nullslast(), FraudRuleSet.created_at.desc())
    )
    if rule_set is None:
        raise AnalysisFailure(
            "ANALYSIS_CONFIGURATION_UNAVAILABLE",
            "No active analysis rule set is available.",
            503,
        )
    fingerprint = request_hash(
        {
            "owner_id": str(user.id),
            "transaction_id": str(transaction.id),
            "confirmation_id": str(confirmation.id),
            "mode": mode.value,
            "policy_version": policy.policy_version,
            "policy_sha256": policy.policy_sha256,
        }
    )
    scope = f"POST:/api/v1/transactions/{transaction.id}/analyses"
    try:
        record, claimed = claim_idempotency(user, scope, idempotency_key, fingerprint)
    except VerificationFailure as failure:
        raise AnalysisFailure(failure.code, failure.message, failure.status) from None
    if not claimed:
        if record.request_hash != fingerprint:
            raise AnalysisFailure(
                "IDEMPOTENCY_KEY_REUSED",
                "This Idempotency-Key was already used for a different analysis request.",
                409,
            )
        return _replay_result(record.resource_id, transaction)

    written_keys: tuple[str, ...] = ()
    try:
        now = datetime.now(UTC)
        image_model = _active_model("IMAGE")
        run = AnalysisRun(
            transaction_id=transaction.id,
            ocr_confirmation_id=confirmation.id,
            status="PROCESSING",
            current_stage="SNAPSHOT",
            template_id=confirmation.ocr_result.template_id,
            rule_set_id=rule_set.id,
            image_model_id=image_model.id if image_model is not None else None,
            structured_model_id=None,
            idempotency_key_hash=record.key_hash,
            request_fingerprint=fingerprint,
            attempt_count=1,
            queued_at=now,
            started_at=now,
            component_scores={},
            top_reasons=[],
            configuration_snapshot={
                "evidence_mode": mode.value,
                "policy_version": policy.policy_version,
                "policy_sha256": policy.policy_sha256,
                "rule_set_version": rule_set.version,
                "ocr_pipeline_version": confirmation.ocr_result.pipeline_version,
                "ocr_engine": confirmation.ocr_result.engine_name,
                "ocr_engine_version": confirmation.ocr_result.engine_version,
                "ocr_confirmation_schema": confirmation.schema_version,
                "receipt_sha256": transaction.receipt.sha256
                if transaction.receipt is not None
                else None,
                "image_forensics_version": current_app.config["IMAGE_FORENSICS_VERSION"],
                "image_model_version": image_model.version if image_model is not None else None,
                "structured_model_version": None,
            },
        )
        db.session.add(run)
        db.session.flush()
        stages: list[AnalysisStageRun] = []

        started_at, counter = _stage_start(run, "SNAPSHOT")
        stages.append(
            _record_stage(
                run,
                "SNAPSHOT",
                started_at,
                counter,
                status="COMPLETED",
                details={
                    "policy_version": policy.policy_version,
                    "mode": mode.value,
                    "confirmation_schema": confirmation.schema_version,
                },
            )
        )

        started_at, counter = _stage_start(run, "VERIFICATION")
        verification_outcome = evaluate_verification(confirmation.confirmed_fields)
        warnings = list(
            dict.fromkeys(
                verification_outcome.warnings
                + verification_reuse_warnings(transaction, verification_outcome.reference)
            )
        )
        verification = VerificationResult(
            analysis_run_id=run.id,
            reference_transaction_id=(
                verification_outcome.reference.id
                if verification_outcome.reference is not None
                else None
            ),
            status=verification_outcome.status,
            verifier_version=verification_outcome.verifier_version,
            candidate_method=verification_outcome.candidate_method,
            field_comparisons=verification_outcome.comparisons,
            matched_field_count=verification_outcome.matched_count,
            mismatched_field_count=verification_outcome.mismatched_count,
            warnings=warnings,
        )
        db.session.add(verification)
        stages.append(
            _record_stage(
                run,
                "VERIFICATION",
                started_at,
                counter,
                status="COMPLETED",
                details={
                    "status": verification_outcome.status,
                    "matched_field_count": verification_outcome.matched_count,
                    "mismatched_field_count": verification_outcome.mismatched_count,
                    "verifier_version": verification_outcome.verifier_version,
                    "warning_codes": warnings,
                },
            )
        )

        started_at, counter = _stage_start(run, "DETERMINISTIC_IMAGE")
        image_analysis: ImageAnalysis | None = None
        image_error_code: str | None = None
        try:
            with db.session.begin_nested():
                image_outcome = run_image_forensics(
                    run=run,
                    transaction=transaction,
                    ocr_result=confirmation.ocr_result,
                    storage=storage,
                )
                image_analysis = image_outcome.image_analysis
                written_keys = image_outcome.written_keys
            image_status = "COMPLETED"
        except ImageForensicsFailure as failure:
            image_status = "FAILED"
            image_error_code = failure.code
        stages.append(
            _record_stage(
                run,
                "DETERMINISTIC_IMAGE",
                started_at,
                counter,
                status=image_status,
                error_code=image_error_code,
                details={
                    "algorithm_version": current_app.config["IMAGE_FORENSICS_VERSION"],
                    "supporting_evidence_only": True,
                    "final_classification_emitted": False,
                },
            )
        )

        started_at, counter = _stage_start(run, "IMAGE_MODEL")
        if image_model is None:
            image_signal = ModelPolicySignal.unavailable("IMAGE", "IMAGE_MODEL_NOT_ACTIVE")
            image_model_status = "SKIPPED"
            image_model_error = "IMAGE_MODEL_NOT_ACTIVE"
        else:
            try:
                if transaction.receipt is None:
                    raise ImageModelFailure(
                        "IMAGE_MODEL_INPUT_UNAVAILABLE",
                        "The receipt image is unavailable for model inference.",
                    )
                image_payload = storage.read_bytes(transaction.receipt.object_key)
                prediction = predict_image_tampering(image_model, image_payload)
                probability = _numeric_prediction_value(prediction, "tamper_probability")
                predicted_class = canonical_image_from_legacy(
                    str(prediction["predicted_class"])
                ).value
                image_signal = ModelPolicySignal(
                    kind="IMAGE",
                    available=True,
                    score=probability,
                    predicted_class=predicted_class,
                    reason_codes=("IMAGE_MODEL_SUCCESS",),
                    model_version=image_model.version,
                    artifact_sha256=image_model.artifact_sha256,
                    schema_hash=image_model.input_schema_hash,
                )
                db.session.add(
                    FraudPrediction(
                        analysis_run_id=run.id,
                        model_version_id=image_model.id,
                        prediction_type="IMAGE",
                        predicted_class=None,
                        probabilities={
                            "unaltered": round(1 - probability, 8),
                            "tampered": round(probability, 8),
                        },
                        feature_schema_hash=image_model.input_schema_hash,
                        feature_snapshot={
                            "threshold": prediction["threshold"],
                            "preprocessing_version": prediction["preprocessing_version"],
                        },
                        inference_ms=_numeric_prediction_value(
                            prediction, "inference_ms", integer=True
                        ),
                        status="SUCCESS",
                    )
                )
                image_model_status = "COMPLETED"
                image_model_error = None
            except (ImageModelFailure, OSError) as failure:
                code = (
                    failure.code
                    if isinstance(failure, ImageModelFailure)
                    else "IMAGE_MODEL_INPUT_UNAVAILABLE"
                )
                image_signal = ModelPolicySignal.unavailable("IMAGE", code)
                db.session.add(
                    FraudPrediction(
                        analysis_run_id=run.id,
                        model_version_id=image_model.id,
                        prediction_type="IMAGE",
                        predicted_class=None,
                        probabilities={},
                        feature_schema_hash=image_model.input_schema_hash,
                        feature_snapshot={},
                        inference_ms=None,
                        status="ERROR",
                        error_code=code,
                    )
                )
                image_model_status = "FAILED"
                image_model_error = code
        stages.append(
            _record_stage(
                run,
                "IMAGE_MODEL",
                started_at,
                counter,
                status=image_model_status,
                error_code=image_model_error,
                details={
                    "model_version": image_signal.model_version,
                    "status": "SUCCESS" if image_signal.available else "UNAVAILABLE",
                },
            )
        )

        started_at, counter = _stage_start(run, "STRUCTURED_MODEL")
        structured_signal = ModelPolicySignal.unavailable(
            "STRUCTURED", "STRUCTURED_CONTEXT_UNAVAILABLE"
        )
        stages.append(
            _record_stage(
                run,
                "STRUCTURED_MODEL",
                started_at,
                counter,
                status="SKIPPED",
                error_code="STRUCTURED_CONTEXT_UNAVAILABLE",
                details={
                    "exact_feature_contract_present": False,
                    "synthetic_defaults_used": False,
                },
            )
        )

        started_at, counter = _stage_start(run, "SEMANTIC_RULES")
        deterministic_reasons = _deterministic_reasons(image_analysis)
        stages.append(
            _record_stage(
                run,
                "SEMANTIC_RULES",
                started_at,
                counter,
                status="COMPLETED",
                details={
                    "deterministic_supporting_reason_count": len(deterministic_reasons),
                    "risk_and_verification_separate": True,
                },
            )
        )

        started_at, counter = _stage_start(run, "RISK_POLICY")
        critical_fields = ("amount", "transaction_reference")
        critical_mismatches = tuple(
            field
            for field in critical_fields
            if verification_outcome.comparisons.get(field, {}).get("status") == "MISMATCH"
        )
        confirmed_complete = all(
            str(confirmation.confirmed_fields.get(field, "")).strip() for field in critical_fields
        )
        policy_result = evaluate_risk_policy(
            policy,
            AnalysisPolicyInput(
                mode=mode,
                verification_status=verification_outcome.status,
                critical_verification_mismatches=critical_mismatches,
                confirmed_critical_fields_complete=confirmed_complete,
                corrected_low_confidence_fields=_corrected_low_confidence_fields(confirmation),
                deterministic_image_reasons=deterministic_reasons,
                image_model=image_signal,
                structured_model=structured_signal,
                semantic_reasons=(),
            ),
        )
        stages.append(
            _record_stage(
                run,
                "RISK_POLICY",
                started_at,
                counter,
                status="COMPLETED",
                details={
                    "policy_version": policy_result.policy_version,
                    "band": policy_result.band.value,
                    "categorical_score_is_null": policy_result.score is None,
                    "reason_codes": [reason.code for reason in policy_result.reasons],
                },
            )
        )

        started_at, counter = _stage_start(run, "FINALIZE")
        run.status = policy_result.status
        run.risk_class = policy_result.legacy_risk_class
        run.risk_score = (
            Decimal(str(policy_result.score * 100)) if policy_result.score is not None else None
        )
        run.component_scores = {
            "verification": {"status": verification_outcome.status},
            "deterministic_image": {
                "status": "COMPLETED" if image_analysis is not None else "UNAVAILABLE",
                "reason_code": image_error_code,
            },
            "image_model": _model_projection(image_signal),
            "structured_model": _model_projection(structured_signal),
            "policy": policy_result.as_dict(),
        }
        run.top_reasons = [reason.as_dict() for reason in policy_result.reasons]
        run.completed_at = datetime.now(UTC)
        run.error_code = (
            "ANALYSIS_EVIDENCE_INCONCLUSIVE" if policy_result.status == "PARTIAL" else None
        )
        run.error_message_safe = (
            "Some analysis components were unavailable; the persisted result is inconclusive."
            if policy_result.status == "PARTIAL"
            else None
        )
        transaction.status = policy_result.status
        transaction.latest_analysis_run_id = run.id
        record.resource_type = "analysis_run"
        record.resource_id = run.id
        record.response_status = 202
        stages.append(
            _record_stage(
                run,
                "FINALIZE",
                started_at,
                counter,
                status="COMPLETED",
                details={
                    "analysis_status": policy_result.status,
                    "band": policy_result.band.value,
                    "automated_evidence_immutable": True,
                },
            )
        )
        run.current_stage = "FINALIZE"
        audit_event(
            "analysis.completed",
            "SUCCESS",
            actor_id=user.id,
            roles=roles,
            target_type="analysis_run",
            target_id=run.id,
            metadata={
                "transaction_id": str(transaction.id),
                "analysis_status": policy_result.status,
                "risk_band": policy_result.band.value,
                "verification_status": verification_outcome.status,
                "policy_version": policy_result.policy_version,
                "image_model_status": ("SUCCESS" if image_signal.available else "UNAVAILABLE"),
                "structured_model_status": "UNAVAILABLE",
            },
        )
        db.session.commit()
        return AnalysisOrchestrationResult(
            run=run,
            verification=verification,
            image_analysis=image_analysis,
            stages=tuple(stages),
            replayed=False,
        )
    except PolicyFailure as failure:
        db.session.rollback()
        for key in reversed(written_keys):
            try:
                storage.delete(key)
            except Exception:
                current_app.logger.exception("analysis_policy_cleanup_failed")
        raise AnalysisFailure(failure.code, failure.message, 503) from None
    except AnalysisFailure:
        db.session.rollback()
        raise
    except Exception:
        db.session.rollback()
        for key in reversed(written_keys):
            try:
                storage.delete(key)
            except Exception:
                current_app.logger.exception("analysis_persistence_cleanup_failed")
        current_app.logger.exception("analysis_orchestration_failed")
        raise AnalysisFailure(
            "ANALYSIS_PERSISTENCE_UNAVAILABLE",
            "The analysis could not be stored safely. Retry with the same key.",
            503,
        ) from None


__all__ = [
    "ANALYSIS_STAGES",
    "AnalysisFailure",
    "AnalysisOrchestrationResult",
    "run_analysis",
]
