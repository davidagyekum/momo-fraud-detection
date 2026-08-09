"""Schemas for administrator-managed user accounts."""

from marshmallow import Schema, fields, validate

from momo_fdvs.api.v1.schemas import MetaSchema

VALID_ROLES = ("USER", "ADMIN", "INVESTIGATOR")
VALID_STATUSES = ("ACTIVE", "DISABLED", "PENDING")


class AdminUserSchema(Schema):
    id = fields.UUID(required=True)
    full_name = fields.String(required=True)
    email = fields.Email(required=True)
    phone_e164 = fields.String(allow_none=True)
    roles = fields.List(fields.String(), required=True)
    status = fields.String(required=True)
    must_change_password = fields.Boolean(required=True)
    version = fields.String(required=True)


class AdminUserEnvelopeSchema(Schema):
    data = fields.Nested(AdminUserSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class AdminUserListDataSchema(Schema):
    users = fields.List(fields.Nested(AdminUserSchema), required=True)
    page = fields.Integer(required=True)
    page_size = fields.Integer(required=True)
    total = fields.Integer(required=True)


class AdminUserListEnvelopeSchema(Schema):
    data = fields.Nested(AdminUserListDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class AdminUserQuerySchema(Schema):
    status = fields.String(validate=validate.OneOf(VALID_STATUSES))
    role = fields.String(validate=validate.OneOf(VALID_ROLES))
    search = fields.String(validate=validate.Length(max=150))
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Integer(load_default=25, validate=validate.Range(min=1, max=100))


class AdminUserCreateSchema(Schema):
    full_name = fields.String(required=True, validate=validate.Length(min=2, max=150))
    email = fields.Email(required=True)
    phone_e164 = fields.String(allow_none=True, validate=validate.Length(max=20))
    password = fields.String(
        required=True, load_only=True, validate=validate.Length(min=12, max=256)
    )
    roles = fields.List(
        fields.String(validate=validate.OneOf(VALID_ROLES)),
        required=True,
        validate=validate.Length(min=1),
    )


class AdminUserUpdateSchema(Schema):
    full_name = fields.String(validate=validate.Length(min=2, max=150))
    phone_e164 = fields.String(allow_none=True, validate=validate.Length(max=20))
    status = fields.String(validate=validate.OneOf(VALID_STATUSES))
    expected_version = fields.String(required=True, load_only=True)


class AdminRoleUpdateSchema(Schema):
    roles = fields.List(
        fields.String(validate=validate.OneOf(VALID_ROLES)),
        required=True,
        validate=validate.Length(min=1),
    )
    expected_version = fields.String(required=True, load_only=True)
