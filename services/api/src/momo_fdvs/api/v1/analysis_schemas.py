"""Schemas for immutable analysis evidence projections."""

from marshmallow import Schema, fields

from momo_fdvs.api.v1.schemas import MetaSchema


class AnalysisEvidenceDataSchema(Schema):
    analysis_run_id = fields.UUID(required=True)
    transaction_id = fields.UUID(required=True)
    status = fields.String(required=True)
    current_stage = fields.String(allow_none=True)
    automated_evidence_immutable = fields.Boolean(required=True)
    risk = fields.Dict(keys=fields.String(), values=fields.Raw(), required=True)
    verification = fields.Dict(
        keys=fields.String(), values=fields.Raw(), allow_none=True, required=True
    )
    image_evidence = fields.Dict(keys=fields.String(), values=fields.Raw(), required=True)
    stages = fields.List(fields.Dict(keys=fields.String(), values=fields.Raw()), required=True)
    configuration_versions = fields.Dict(keys=fields.String(), values=fields.Raw(), required=True)


class AnalysisEvidenceEnvelopeSchema(Schema):
    data = fields.Nested(AnalysisEvidenceDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


__all__ = ["AnalysisEvidenceEnvelopeSchema"]
