"""Marshmallow schemas that generate the P01 OpenAPI contract."""

from marshmallow import Schema, fields


class MetaSchema(Schema):
    request_id = fields.UUID(required=True)


class HealthDataSchema(Schema):
    status = fields.String(required=True)
    service = fields.String(required=True)
    version = fields.String(required=True)


class HealthEnvelopeSchema(Schema):
    data = fields.Nested(HealthDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class ComponentSchema(Schema):
    status = fields.String(required=True)
    reason = fields.String(load_default=None, allow_none=True)
    version = fields.String(load_default=None, allow_none=True)


class ReadinessComponentsSchema(Schema):
    database = fields.Nested(ComponentSchema, required=True)
    storage = fields.Nested(ComponentSchema, required=True)
    tesseract = fields.Nested(ComponentSchema, required=True)
    structured_model = fields.Nested(ComponentSchema, required=True)
    image_model = fields.Nested(ComponentSchema, required=True)


class ReadinessDataSchema(Schema):
    ready = fields.Boolean(required=True)
    components = fields.Nested(ReadinessComponentsSchema, required=True)
    analysis_available = fields.Boolean(required=True)
    full_analysis_available = fields.Boolean(required=True)


class ReadinessEnvelopeSchema(Schema):
    data = fields.Nested(ReadinessDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class VersionDataSchema(Schema):
    application = fields.String(required=True)
    version = fields.String(required=True)
    build_commit = fields.String(required=True)
    api_contract_version = fields.String(required=True)


class VersionEnvelopeSchema(Schema):
    data = fields.Nested(VersionDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class ErrorDataSchema(Schema):
    code = fields.String(required=True)
    message = fields.String(required=True)
    field_errors = fields.Dict(
        keys=fields.String(),
        values=fields.List(fields.String()),
        load_default=None,
        allow_none=True,
    )
    request_id = fields.UUID(required=True)


class ErrorEnvelopeSchema(Schema):
    error = fields.Nested(ErrorDataSchema, required=True)
