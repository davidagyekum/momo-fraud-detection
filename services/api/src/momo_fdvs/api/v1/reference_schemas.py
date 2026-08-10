"""Schemas for private reference imports and stored-record verification."""

from marshmallow import Schema, fields, validate

from momo_fdvs.api.v1.schemas import MetaSchema


class ReferenceImportQuerySchema(Schema):
    status = fields.String(
        validate=validate.OneOf(("UPLOADED", "VALIDATED", "COMMITTED", "FAILED"))
    )
    search = fields.String(validate=validate.Length(max=150))
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Integer(load_default=25, validate=validate.Range(min=1, max=100))


class ReferenceTransactionQuerySchema(Schema):
    provider_code = fields.String(validate=validate.Length(max=50))
    search = fields.String(validate=validate.Length(max=150))
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Integer(load_default=25, validate=validate.Range(min=1, max=100))


class ReferenceImportSchema(Schema):
    id = fields.UUID(required=True)
    source_label = fields.String(required=True)
    original_filename = fields.String(required=True)
    file_sha256 = fields.String(required=True)
    status = fields.String(required=True)
    total_rows = fields.Integer(required=True)
    valid_rows = fields.Integer(required=True)
    invalid_rows = fields.Integer(required=True)
    uploaded_by = fields.UUID(required=True)
    validated_at = fields.DateTime(allow_none=True)
    committed_at = fields.DateTime(allow_none=True)
    created_at = fields.DateTime(required=True)
    invalid_rows_download = fields.String(allow_none=True)


class ReferenceImportEnvelopeSchema(Schema):
    data = fields.Nested(ReferenceImportSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class ReferenceImportListDataSchema(Schema):
    imports = fields.List(fields.Nested(ReferenceImportSchema), required=True)
    page = fields.Integer(required=True)
    page_size = fields.Integer(required=True)
    total = fields.Integer(required=True)


class ReferenceImportListEnvelopeSchema(Schema):
    data = fields.Nested(ReferenceImportListDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class ReferenceValidationSchema(Schema):
    batch = fields.Nested(ReferenceImportSchema, required=True)
    batch_id = fields.UUID(required=True)
    status = fields.String(required=True)
    total_rows = fields.Integer(required=True)
    valid_rows = fields.Integer(required=True)
    invalid_rows = fields.Integer(required=True)
    invalid_rows_download = fields.String(allow_none=True)
    errors = fields.List(fields.Dict(keys=fields.String(), values=fields.Raw()), required=True)
    preview_truncated = fields.Boolean(required=True)


class ReferenceValidationEnvelopeSchema(Schema):
    data = fields.Nested(ReferenceValidationSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class ReferenceCommitSchema(Schema):
    batch = fields.Nested(ReferenceImportSchema, required=True)
    committed_rows = fields.Integer(required=True)
    replayed = fields.Boolean(required=True)


class ReferenceCommitEnvelopeSchema(Schema):
    data = fields.Nested(ReferenceCommitSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class ReferenceTransactionSchema(Schema):
    id = fields.UUID(required=True)
    provider_code = fields.String(required=True)
    transaction_reference_masked = fields.String(required=True)
    amount = fields.String(required=True)
    currency = fields.String(required=True)
    sender_phone_masked = fields.String(allow_none=True)
    receiver_phone_masked = fields.String(allow_none=True)
    occurred_at = fields.DateTime(allow_none=True)
    transaction_status = fields.String(allow_none=True)
    source_label = fields.String(required=True)
    import_batch_id = fields.UUID(required=True)
    created_at = fields.DateTime(required=True)


class ReferenceTransactionEnvelopeSchema(Schema):
    data = fields.Nested(ReferenceTransactionSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class ReferenceTransactionListDataSchema(Schema):
    references = fields.List(fields.Nested(ReferenceTransactionSchema), required=True)
    page = fields.Integer(required=True)
    page_size = fields.Integer(required=True)
    total = fields.Integer(required=True)


class ReferenceTransactionListEnvelopeSchema(Schema):
    data = fields.Nested(ReferenceTransactionListDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class PartialAnalysisDataSchema(Schema):
    analysis_id = fields.UUID(required=True)
    analysis_run_id = fields.UUID(required=True)
    transaction_id = fields.UUID(required=True)
    status = fields.String(required=True)
    current_stage = fields.String(required=True)
    risk = fields.Dict(keys=fields.String(), values=fields.Raw(), required=True)
    verification = fields.Dict(keys=fields.String(), values=fields.Raw(), required=True)
    unavailable_stages = fields.List(fields.String(), required=True)
    replayed = fields.Boolean(required=True)


class PartialAnalysisEnvelopeSchema(Schema):
    data = fields.Nested(PartialAnalysisDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)
