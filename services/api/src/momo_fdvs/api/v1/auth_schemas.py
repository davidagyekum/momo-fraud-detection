"""Authentication and identity API schemas."""

from marshmallow import Schema, fields, validate

from momo_fdvs.api.v1.schemas import MetaSchema


class RegisterSchema(Schema):
    full_name = fields.String(required=True, validate=validate.Length(min=2, max=150))
    email = fields.Email(required=True)
    password = fields.String(
        required=True, load_only=True, validate=validate.Length(min=12, max=256)
    )


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True, load_only=True)


class RefreshSchema(Schema):
    refresh_token = fields.String(load_default=None, allow_none=True, load_only=True)


class ForgotPasswordSchema(Schema):
    email = fields.Email(required=True)


class ResetPasswordSchema(Schema):
    token = fields.String(required=True, load_only=True)
    new_password = fields.String(
        required=True, load_only=True, validate=validate.Length(min=12, max=256)
    )


class ChangePasswordSchema(Schema):
    current_password = fields.String(required=True, load_only=True)
    new_password = fields.String(
        required=True, load_only=True, validate=validate.Length(min=12, max=256)
    )


class UserSchema(Schema):
    id = fields.UUID(required=True)
    full_name = fields.String(required=True)
    email = fields.Email(required=True)
    phone_e164 = fields.String(allow_none=True)
    roles = fields.List(fields.String(), required=True)
    status = fields.String(required=True)
    must_change_password = fields.Boolean(required=True)


class SessionDataSchema(Schema):
    access_token = fields.String(required=True)
    refresh_token = fields.String(load_default=None, allow_none=True)
    csrf_token = fields.String(load_default=None, allow_none=True)
    expires_in = fields.Integer(required=True)
    user = fields.Nested(UserSchema, required=True)


class SessionEnvelopeSchema(Schema):
    data = fields.Nested(SessionDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class UserEnvelopeSchema(Schema):
    data = fields.Nested(UserSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class AcceptedDataSchema(Schema):
    accepted = fields.Boolean(required=True)


class AcceptedEnvelopeSchema(Schema):
    data = fields.Nested(AcceptedDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class ProfileUpdateSchema(Schema):
    full_name = fields.String(validate=validate.Length(min=2, max=150))
    phone_e164 = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=20))
