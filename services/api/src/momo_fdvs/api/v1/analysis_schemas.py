"""Schemas for persisted analysis results and immutable evidence projections."""

from marshmallow import Schema, fields, validate

from momo_fdvs.api.v1.schemas import MetaSchema


class PolicyReasonSchema(Schema):
    code = fields.String(required=True)
    title = fields.String(required=True)
    severity = fields.String(required=True)


class AnalysisRiskSchema(Schema):
    status = fields.String(required=True)
    band = fields.String(required=True)
    conclusion_status = fields.String(
        required=True,
        validate=validate.OneOf(("CONCLUSIVE", "INCONCLUSIVE", "FAILED")),
    )
    component_status = fields.String(
        required=True,
        validate=validate.OneOf(("COMPLETE", "DEGRADED", "FAILED")),
    )
    risk_class = fields.String(attribute="class", data_key="class", allow_none=True, required=True)
    score = fields.Float(allow_none=True, required=True)
    summary = fields.String(required=True)
    reasons = fields.List(fields.Nested(PolicyReasonSchema), required=True)
    missing_signals = fields.List(fields.String(), required=True)
    limitations = fields.List(fields.String(), required=True)
    policy_version = fields.String(required=True)
    disclaimer = fields.String(required=True)


class VerificationSummarySchema(Schema):
    status = fields.String(required=True)
    label = fields.String(required=True)
    basis = fields.String(required=True)
    summary = fields.String(required=True)
    reference_transaction_id = fields.UUID(allow_none=True, required=True)
    candidate_method = fields.String(required=True)
    verifier_version = fields.String(required=True)
    rule_set_version = fields.String(allow_none=True, required=True)
    field_comparisons = fields.Dict(keys=fields.String(), values=fields.Raw(), required=True)
    matched_field_count = fields.Integer(required=True)
    mismatched_field_count = fields.Integer(required=True)
    warnings = fields.List(fields.String(), required=True)
    disclaimer = fields.String(required=True)


class ComponentStatusSchema(Schema):
    status = fields.String(required=True)
    reason_code = fields.String(allow_none=True)
    reason_codes = fields.List(fields.String())
    model_version = fields.String(allow_none=True)


class TextFraudComponentSchema(Schema):
    status = fields.String(required=True)
    risk_class = fields.String(attribute="class", data_key="class", allow_none=True, required=True)
    policy_score = fields.Integer(allow_none=True, required=True)
    score_is_probability = fields.Boolean(required=True)
    reason_codes = fields.List(fields.String(), required=True)
    evidence_quality = fields.String(required=True)
    ruleset_version = fields.String(allow_none=True, required=True)
    limitations = fields.List(fields.String(), required=True)


class AnalysisStageSchema(Schema):
    stage = fields.String(required=True)
    status = fields.String(required=True)
    attempt = fields.Integer(required=True)
    duration_ms = fields.Integer(allow_none=True, required=True)
    error_code = fields.String(allow_none=True, required=True)


class AnalysisProgressSchema(Schema):
    current_stage = fields.String(allow_none=True, required=True)
    completed_stage_count = fields.Integer(required=True)
    total_stage_count = fields.Integer(required=True)
    stages = fields.List(fields.Nested(AnalysisStageSchema), required=True)


class AnalysisVersionsSchema(Schema):
    policy_version = fields.String(allow_none=True, required=True)
    policy_sha256 = fields.String(allow_none=True, required=True)
    rule_set_version = fields.String(allow_none=True, required=True)
    ocr_pipeline_version = fields.String(allow_none=True, required=True)
    ocr_engine_version = fields.String(allow_none=True, required=True)
    image_forensics_version = fields.String(allow_none=True, required=True)
    image_model_version = fields.String(allow_none=True, required=True)
    structured_model_version = fields.String(allow_none=True, required=True)
    text_fraud_schema_version = fields.String(allow_none=True, required=True)
    text_fraud_ruleset_version = fields.String(allow_none=True, required=True)


class AnalysisEvidenceSummarySchema(Schema):
    deterministic_image = fields.Nested(ComponentStatusSchema, required=True)
    image_model = fields.Nested(ComponentStatusSchema, required=True)
    structured_model = fields.Nested(ComponentStatusSchema, required=True)
    text_fraud = fields.Nested(TextFraudComponentSchema, required=True)
    automated_evidence_immutable = fields.Boolean(required=True)


class AnalysisOCRReviewSchema(Schema):
    status = fields.String(required=True)
    ocr_result_id = fields.UUID(required=True)
    confirmed_field_count = fields.Integer(required=True)
    correction_count = fields.Integer(required=True)
    schema_version = fields.String(allow_none=True, required=True)


class AnalysisDataSchema(Schema):
    id = fields.UUID(required=True)
    transaction_id = fields.UUID(required=True)
    analysis_mode = fields.String(required=True)
    ocr_result_id = fields.UUID(allow_none=True, required=True)
    ocr_confirmation_id = fields.UUID(allow_none=True, required=True)
    status = fields.String(required=True)
    risk = fields.Nested(AnalysisRiskSchema, required=True)
    verification = fields.Nested(VerificationSummarySchema, allow_none=True, required=True)
    evidence_summary = fields.Nested(AnalysisEvidenceSummarySchema, required=True)
    ocr_review = fields.Nested(AnalysisOCRReviewSchema, required=True)
    versions = fields.Nested(AnalysisVersionsSchema, required=True)
    progress = fields.Nested(AnalysisProgressSchema, required=True)
    evidence_url = fields.String(required=True)
    created_at = fields.DateTime(required=True)
    completed_at = fields.DateTime(allow_none=True, required=True)


class AnalysisEnvelopeSchema(Schema):
    data = fields.Nested(AnalysisDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class AnalysisEvidenceDataSchema(Schema):
    analysis_run_id = fields.UUID(required=True)
    transaction_id = fields.UUID(required=True)
    analysis_mode = fields.String(required=True)
    ocr_result_id = fields.UUID(allow_none=True, required=True)
    ocr_confirmation_id = fields.UUID(allow_none=True, required=True)
    status = fields.String(required=True)
    current_stage = fields.String(allow_none=True)
    automated_evidence_immutable = fields.Boolean(required=True)
    risk = fields.Nested(AnalysisRiskSchema, required=True)
    verification = fields.Nested(VerificationSummarySchema, allow_none=True, required=True)
    image_evidence = fields.Dict(keys=fields.String(), values=fields.Raw(), required=True)
    stages = fields.List(fields.Nested(AnalysisStageSchema), required=True)
    configuration_versions = fields.Nested(AnalysisVersionsSchema, required=True)


class AnalysisEvidenceEnvelopeSchema(Schema):
    data = fields.Nested(AnalysisEvidenceDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


__all__ = [
    "AnalysisEnvelopeSchema",
    "AnalysisEvidenceEnvelopeSchema",
    "AnalysisRiskSchema",
]
