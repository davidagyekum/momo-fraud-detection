"""Receipt submission response schemas."""

from marshmallow import Schema, fields

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
