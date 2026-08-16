"""Owner-safe report API schemas."""

from marshmallow import Schema, fields, validate

from momo_fdvs.api.v1.schemas import MetaSchema


class AnalysisReportCreateSchema(Schema):
    format = fields.String(load_default="HTML", validate=validate.OneOf(("HTML",)))


class ReportArtifactSchema(Schema):
    id = fields.UUID(required=True)
    report_type = fields.String(required=True)
    transaction_id = fields.UUID(allow_none=True, required=True)
    analysis_run_id = fields.UUID(allow_none=True, required=True)
    status = fields.String(required=True)
    sha256 = fields.String(allow_none=True, required=True)
    generated_at = fields.DateTime(allow_none=True, required=True)
    expires_at = fields.DateTime(allow_none=True, required=True)
    download_url = fields.String(allow_none=True, required=True)
    replayed = fields.Boolean(required=True)


class ReportEnvelopeSchema(Schema):
    data = fields.Nested(ReportArtifactSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


__all__ = ["AnalysisReportCreateSchema", "ReportEnvelopeSchema"]
