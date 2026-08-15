"""Owner-safe notification API schemas."""

from marshmallow import Schema, fields, validate

from momo_fdvs.api.v1.schemas import MetaSchema


class NotificationQuerySchema(Schema):
    unread = fields.Boolean(load_default=False)
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Integer(load_default=25, validate=validate.Range(min=1, max=100))


class NotificationTargetSchema(Schema):
    type = fields.String(required=True)
    id = fields.UUID(required=True)


class NotificationSchema(Schema):
    id = fields.UUID(required=True)
    type = fields.String(required=True)
    title = fields.String(required=True)
    message = fields.String(required=True)
    target = fields.Nested(NotificationTargetSchema, allow_none=True, required=True)
    read_at = fields.DateTime(allow_none=True, required=True)
    created_at = fields.DateTime(required=True)


class NotificationListDataSchema(Schema):
    items = fields.List(fields.Nested(NotificationSchema), required=True)
    page = fields.Integer(required=True)
    page_size = fields.Integer(required=True)
    total = fields.Integer(required=True)
    total_pages = fields.Integer(required=True)


class NotificationListEnvelopeSchema(Schema):
    data = fields.Nested(NotificationListDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class NotificationEnvelopeSchema(Schema):
    data = fields.Nested(NotificationSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class UnreadCountDataSchema(Schema):
    unread_count = fields.Integer(required=True)


class UnreadCountEnvelopeSchema(Schema):
    data = fields.Nested(UnreadCountDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class ReadAllDataSchema(Schema):
    marked_read = fields.Integer(required=True)
    unread_count = fields.Integer(required=True)


class ReadAllEnvelopeSchema(Schema):
    data = fields.Nested(ReadAllDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


__all__ = [
    "NotificationEnvelopeSchema",
    "NotificationListEnvelopeSchema",
    "NotificationQuerySchema",
    "ReadAllEnvelopeSchema",
    "UnreadCountEnvelopeSchema",
]
