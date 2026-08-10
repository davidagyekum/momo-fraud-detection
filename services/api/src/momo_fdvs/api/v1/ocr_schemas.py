"""OCR run, review and immutable confirmation API schemas."""

from marshmallow import Schema, fields, validate

from momo_fdvs.api.v1.reference_schemas import PartialAnalysisEnvelopeSchema
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


class OCRReviewDataSchema(Schema):
    transaction_id = fields.UUID(required=True)
    status = fields.String(required=True)
    ocr_result_id = fields.UUID(required=True)
    provider = fields.Nested(OCRProviderSchema, required=True)
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


__all__ = [
    "OCRConfirmationEnvelopeSchema",
    "OCRConfirmationRequestSchema",
    "OCRReviewEnvelopeSchema",
    "PartialAnalysisEnvelopeSchema",
]
