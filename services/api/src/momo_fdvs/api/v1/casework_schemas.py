"""Schemas for owner fraud reports and investigator casework."""

from marshmallow import Schema, fields, validate

from momo_fdvs.api.v1.schemas import MetaSchema
from momo_fdvs.services.casework import CASE_CATEGORIES

CASE_STATUSES = ("OPEN", "ASSIGNED", "IN_REVIEW", "DECIDED", "CLOSED", "REOPENED")
CASE_SOURCES = ("USER_REPORT", "AUTO_HIGH_RISK", "ADMIN")
DECISION_OUTCOMES = ("CONFIRMED", "DISMISSED", "ESCALATED")


class OwnerFraudReportCreateSchema(Schema):
    category = fields.String(required=True, validate=validate.OneOf(CASE_CATEGORIES))
    description = fields.String(allow_none=True, validate=validate.Length(max=2000))


class CaseEventSchema(Schema):
    id = fields.UUID(required=True)
    event_type = fields.String(required=True)
    from_status = fields.String(allow_none=True, required=True)
    to_status = fields.String(allow_none=True, required=True)
    created_at = fields.DateTime(required=True)
    actor_id = fields.UUID(required=False)
    reason = fields.String(allow_none=True, required=False)


class CaseDecisionSchema(Schema):
    id = fields.UUID(required=True)
    outcome = fields.String(required=True)
    reason = fields.String(required=True)
    decided_by = fields.UUID(required=False)
    created_at = fields.DateTime(required=False)


class CaseSchema(Schema):
    id = fields.UUID(required=True)
    transaction_id = fields.UUID(required=True)
    source = fields.String(required=True)
    category = fields.String(required=True)
    status = fields.String(required=True)
    version = fields.Integer(required=True)
    opened_at = fields.DateTime(required=True)
    updated_at = fields.DateTime(required=True)
    description = fields.String(allow_none=True, required=False)
    assigned_to = fields.UUID(allow_none=True, required=False)
    timeline = fields.List(fields.Nested(CaseEventSchema), required=False)
    decisions = fields.List(fields.Nested(CaseDecisionSchema), required=False)
    automated_evidence = fields.Dict(required=False)
    replayed = fields.Boolean(required=False)
    linked_existing = fields.Boolean(required=False)
    decision = fields.Nested(CaseDecisionSchema, required=False)


class CaseEnvelopeSchema(Schema):
    data = fields.Nested(CaseSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class AdminCaseQuerySchema(Schema):
    status = fields.String(validate=validate.OneOf(CASE_STATUSES))
    source = fields.String(validate=validate.OneOf(CASE_SOURCES))
    assigned_to = fields.UUID()
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Integer(load_default=25, validate=validate.Range(min=1, max=100))


class CaseListDataSchema(Schema):
    items = fields.List(fields.Nested(CaseSchema), required=True)
    page = fields.Integer(required=True)
    page_size = fields.Integer(required=True)
    total = fields.Integer(required=True)
    total_pages = fields.Integer(required=True)


class CaseListEnvelopeSchema(Schema):
    data = fields.Nested(CaseListDataSchema, required=True)
    meta = fields.Nested(MetaSchema, required=True)


class CaseAssignSchema(Schema):
    investigator_id = fields.UUID(required=True)
    expected_case_version = fields.Integer(required=True, validate=validate.Range(min=1))


class CaseVersionSchema(Schema):
    expected_case_version = fields.Integer(required=True, validate=validate.Range(min=1))


class CaseNoteSchema(CaseVersionSchema):
    note = fields.String(required=True, validate=validate.Length(min=1, max=4000))


class CaseDecisionCreateSchema(CaseVersionSchema):
    outcome = fields.String(required=True, validate=validate.OneOf(DECISION_OUTCOMES))
    reason = fields.String(required=True, validate=validate.Length(min=1, max=4000))


__all__ = [
    "AdminCaseQuerySchema",
    "CaseAssignSchema",
    "CaseDecisionCreateSchema",
    "CaseEnvelopeSchema",
    "CaseListEnvelopeSchema",
    "CaseNoteSchema",
    "CaseVersionSchema",
    "OwnerFraudReportCreateSchema",
]
