"""Receipt submission and owner-safe transaction history schemas."""

from marshmallow import Schema, fields, validate

from momo_fdvs.api.v1.schemas import MetaSchema


class UploadedTransactionSchema(Schema):
    id = fields.UUID(required=True)
    status = fields.String(required=True)
    created_at = fields.DateTime(required=True)


class ReceiptDimensionsSchema(Schema):
    width_px = fields.Integer(required=True)
    height_px = fields.Integer(required=True)


class ReceiptQualitySchema(Schema):
    score = fields.Float(required=True)
    warnings = fields.List(fields.String(), required=True)


class DuplicateWarningSchema(Schema):
    exact_match_found = fields.Boolean(required=True)
    near_match_found = fields.Boolean(required=True)


class ReceiptMediaSchema(Schema):
    thumbnail_url = fields.String(required=True)
    original_url = fields.String(required=True)


class UploadedReceiptSchema(Schema):
    id = fields.UUID(required=True)
    media_type = fields.String(required=True)
    size_bytes = fields.Integer(required=True)
    width_px = fields.Integer(required=True)
    height_px = fields.Integer(required=True)
    quality_warnings = fields.List(fields.String(), required=True)
    dimensions = fields.Nested(ReceiptDimensionsSchema, required=True)
    quality = fields.Nested(ReceiptQualitySchema, required=True)
    duplicate_warning = fields.Nested(DuplicateWarningSchema, required=True)
    media = fields.Nested(ReceiptMediaSchema, required=True)


class NextActionSchema(Schema):
    type = fields.String(required=True)
    endpoint = fields.String(required=True)


class TransactionUploadDataSchema(Schema):
    transaction = fields.Nested(UploadedTransactionSchema, required=True)
    receipt = fields.Nested(UploadedReceiptSchema, required=True)
    next_action = fields.Nested(NextActionSchema, required=True)
    replayed = fields.Boolean(required=True)


class TransactionUploadEnvelopeSchema(Schema):
    data = fields.Nested(TransactionUploadDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class TransactionHistoryQuerySchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    provider = fields.String()
    status = fields.String(
        validate=validate.OneOf(
            [
                "DRAFT",
                "UPLOADED",
                "OCR_PENDING",
                "OCR_REVIEW",
                "READY",
                "ANALYSIS_QUEUED",
                "ANALYSING",
                "COMPLETED",
                "PARTIAL",
                "FAILED",
            ]
        )
    )
    verification = fields.String(validate=validate.OneOf(["VERIFIED", "UNVERIFIED", "MISMATCH"]))
    band = fields.String(
        validate=validate.OneOf(["low_risk", "medium_risk", "high_risk", "inconclusive"])
    )


class TransactionAnalysisSummarySchema(Schema):
    id = fields.UUID(required=True)
    status = fields.String(required=True)
    band = fields.String(required=True)
    risk_class = fields.String(attribute="class", data_key="class", allow_none=True, required=True)
    score = fields.Float(allow_none=True, required=True)
    verification_status = fields.String(allow_none=True, required=True)
    completed_at = fields.DateTime(allow_none=True, required=True)
    policy_version = fields.String(required=True)


class TransactionSummarySchema(Schema):
    id = fields.UUID(required=True)
    status = fields.String(required=True)
    provider_code = fields.String(allow_none=True, required=True)
    display_reference_masked = fields.String(allow_none=True, required=True)
    created_at = fields.DateTime(required=True)
    updated_at = fields.DateTime(required=True)
    thumbnail_url = fields.String(allow_none=True, required=True)
    owner_visible = fields.Boolean(required=True)
    latest_analysis = fields.Nested(
        TransactionAnalysisSummarySchema, allow_none=True, required=True
    )


class TransactionHistoryDataSchema(Schema):
    items = fields.List(fields.Nested(TransactionSummarySchema), required=True)
    page = fields.Integer(required=True)
    page_size = fields.Integer(required=True)
    total = fields.Integer(required=True)
    total_pages = fields.Integer(required=True)


class TransactionHistoryEnvelopeSchema(Schema):
    data = fields.Nested(TransactionHistoryDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class ConfirmedFieldCoverageSchema(Schema):
    field_count = fields.Integer(required=True)
    correction_count = fields.Integer(required=True)
    schema_version = fields.String(allow_none=True, required=True)


class TransactionDetailSchema(TransactionSummarySchema):
    confirmed_field_coverage = fields.Nested(ConfirmedFieldCoverageSchema, required=True)
    analysis_runs = fields.List(fields.Nested(TransactionAnalysisSummarySchema), required=True)


class TransactionDetailEnvelopeSchema(Schema):
    data = fields.Nested(TransactionDetailSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


__all__ = [
    "TransactionDetailEnvelopeSchema",
    "TransactionHistoryEnvelopeSchema",
    "TransactionHistoryQuerySchema",
    "TransactionUploadEnvelopeSchema",
]
