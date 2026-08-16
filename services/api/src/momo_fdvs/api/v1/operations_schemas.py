"""Schemas for bounded staff operational views."""

from marshmallow import Schema, fields, validate

from momo_fdvs.api.v1.schemas import MetaSchema


class PageQuerySchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Integer(load_default=25, validate=validate.Range(min=1, max=100))


class TransactionQuerySchema(PageQuerySchema):
    status = fields.String(validate=validate.Length(max=30))
    provider = fields.String(validate=validate.Length(max=50))


class AuditQuerySchema(PageQuerySchema):
    action = fields.String(validate=validate.Length(max=100))
    outcome = fields.String(validate=validate.OneOf(("SUCCESS", "FAILURE", "DENIED")))


class OperationalDataEnvelopeSchema(Schema):
    data = fields.Dict(keys=fields.String(), values=fields.Raw(), required=True)
    meta = fields.Nested(MetaSchema, required=True)


__all__ = [
    "AuditQuerySchema",
    "OperationalDataEnvelopeSchema",
    "PageQuerySchema",
    "TransactionQuerySchema",
]
