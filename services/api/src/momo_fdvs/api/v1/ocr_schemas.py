"""OCR run, review and immutable confirmation API schemas."""

from marshmallow import Schema, fields, validate

from momo_fdvs.api.v1.schemas import MetaSchema


class OCRProviderSchema(Schema):
    value = fields.String(required=True)
    confidence = fields.Float(required=True)
    requires_review = fields.Boolean(required=True)
    warnings = fields.List(fields.String(), required=True)


class OCRFieldSchema(Schema):
    raw_value = fields.Raw(allow_none=True)
    value = fields.Raw(allow_none=True)
    confidence = fields.Float(required=True)
    valid = fields.Boolean(required=True)
    requires_review = fields.Boolean(required=True)
    source_token_ids = fields.List(fields.Integer(), required=True)
    warnings = fields.List(fields.String(), required=True)
    currency = fields.String(allow_none=True)
    masked = fields.String(allow_none=True)


class OCRTextFraudReasonSchema(Schema):
    code = fields.String(required=True)
    title = fields.String(required=True)
    summary = fields.String(required=True)
    severity = fields.String(required=True)


class OCRTextFraudPreviewSchema(Schema):
    schema_version = fields.String(required=True)
    ruleset_version = fields.String(required=True)
    status = fields.String(required=True)
    risk_class = fields.String(attribute="class", data_key="class", allow_none=True, required=True)
    score = fields.Integer(allow_none=True, required=True)
    score_is_probability = fields.Boolean(required=True)
    reason_code = fields.String(required=True)
    reason_codes = fields.List(fields.String(), required=True)
    reasons = fields.List(fields.Nested(OCRTextFraudReasonSchema), required=True)
    evidence_quality = fields.String(required=True)
    limitations = fields.List(fields.String(), required=True)
    summary = fields.String(required=True)
    disclaimer = fields.String(required=True)


class OCRReviewDataSchema(Schema):
    transaction_id = fields.UUID(required=True)
    status = fields.String(required=True)
    ocr_result_id = fields.UUID(required=True)
    provider = fields.Nested(OCRProviderSchema, required=True)
    fraud_preview = fields.Nested(OCRTextFraudPreviewSchema, required=True)
    ocr_fields = fields.Dict(
        keys=fields.String(),
        values=fields.Nested(OCRFieldSchema),
        attribute="fields",
        data_key="fields",
        required=True,
    )
    warnings = fields.List(fields.String(), required=True)
    raw_text = fields.String(required=True)
    selected_variant = fields.String(required=True)
    pipeline_version = fields.String(required=True)
    engine_version = fields.String(required=True)
    preview_url = fields.String(required=True)
    confirmation_endpoint = fields.String(required=True)
    replayed = fields.Boolean(required=True)


class OCRReviewEnvelopeSchema(Schema):
    data = fields.Nested(OCRReviewDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class OCRConfirmationRequestSchema(Schema):
    ocr_result_id = fields.UUID(required=True)
    confirmed_fields = fields.Dict(
        keys=fields.String(), values=fields.Raw(), data_key="fields", required=True
    )
    correction_reasons = fields.Dict(
        keys=fields.String(),
        values=fields.String(validate=validate.Length(min=5, max=300)),
        load_default=dict,
    )


class OCRConfirmationDataSchema(Schema):
    confirmation_id = fields.UUID(required=True)
    ocr_result_id = fields.UUID(required=True)
    transaction_id = fields.UUID(required=True)
    status = fields.String(required=True)
    schema_version = fields.String(required=True)
    corrected_fields = fields.List(fields.String(), required=True)
    replayed = fields.Boolean(required=True)
    next_action = fields.Dict(keys=fields.String(), values=fields.Raw(), required=True)


class OCRConfirmationEnvelopeSchema(Schema):
    data = fields.Nested(OCRConfirmationDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class AnalysisUnavailableDataSchema(Schema):
    transaction_id = fields.UUID(required=True)
    status = fields.String(required=True)
    available = fields.Boolean(required=True)


class AnalysisUnavailableEnvelopeSchema(Schema):
    data = fields.Nested(AnalysisUnavailableDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class AnalysisStartDataSchema(Schema):
    analysis_run_id = fields.UUID(required=True)
    transaction_id = fields.UUID(required=True)
    status = fields.String(required=True)
    current_stage = fields.String(allow_none=True, required=True)
    poll_url = fields.String(required=True)
    replayed = fields.Boolean(required=True)


class AnalysisStartEnvelopeSchema(Schema):
    data = fields.Nested(AnalysisStartDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


__all__ = [
    "AnalysisStartEnvelopeSchema",
    "OCRConfirmationEnvelopeSchema",
    "OCRConfirmationRequestSchema",
    "OCRReviewEnvelopeSchema",
]
