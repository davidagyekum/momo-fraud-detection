"""Owner fraud reporting and staff investigation endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from flask import g, request
from flask.views import MethodView
from flask_smorest import Blueprint

from momo_fdvs.api.v1.casework_schemas import (
    AdminCaseQuerySchema,
    CaseAssignSchema,
    CaseDecisionCreateSchema,
    CaseEnvelopeSchema,
    CaseListEnvelopeSchema,
    CaseNoteSchema,
    CaseVersionSchema,
    OwnerFraudReportCreateSchema,
)
from momo_fdvs.errors import error_response
from momo_fdvs.extensions import db
from momo_fdvs.policies.auth import require_roles
from momo_fdvs.services.casework import (
    CaseworkFailure,
    add_note,
    assign_case,
    case_summary,
    create_or_link_owner_case,
    get_owner_case,
    get_staff_case,
    list_cases,
    owner_case_projection,
    record_decision,
    staff_case_projection,
    start_review,
)

casework_blueprint = Blueprint(
    "casework-v1",
    __name__,
    url_prefix="/api/v1",
    description="Owner fraud reporting and append-only investigator casework",
)


def _meta() -> dict[str, str]:
    return {"request_id": g.request_id}


def _failure(failure: CaseworkFailure) -> Any:
    db.session.rollback()
    return error_response(failure.code, failure.message, failure.status)


@casework_blueprint.route("/transactions/<uuid:transaction_id>/fraud-reports")
class OwnerFraudReportResource(MethodView):
    @require_roles("USER")
    @casework_blueprint.arguments(OwnerFraudReportCreateSchema)
    @casework_blueprint.alt_response(200, schema=CaseEnvelopeSchema)
    @casework_blueprint.response(201, CaseEnvelopeSchema)
    def post(self, data: dict[str, Any], transaction_id: uuid.UUID) -> Any:
        key = request.headers.get("Idempotency-Key", "").strip()
        if not key:
            return error_response("IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key is required.", 400)
        try:
            result = create_or_link_owner_case(
                transaction_id=transaction_id,
                category=data["category"],
                description=data.get("description"),
                user=g.current_user,
                roles=set(g.current_roles),
                idempotency_key=key,
            )
            projection = {
                **case_summary(result.case),
                "replayed": result.replayed,
                "linked_existing": result.linked_existing,
            }
            status = 200 if result.replayed or result.linked_existing else 201
            return {"data": projection, "meta": _meta()}, status
        except CaseworkFailure as failure:
            return _failure(failure)


@casework_blueprint.route("/fraud-reports/<uuid:case_id>")
class OwnerFraudReportDetailResource(MethodView):
    @require_roles("USER")
    @casework_blueprint.response(200, CaseEnvelopeSchema)
    def get(self, case_id: uuid.UUID) -> Any:
        try:
            case = get_owner_case(case_id, g.current_user.id)
            return {"data": owner_case_projection(case), "meta": _meta()}
        except CaseworkFailure as failure:
            return _failure(failure)


@casework_blueprint.route("/admin/cases")
class AdminCasesResource(MethodView):
    @require_roles("ADMIN", "INVESTIGATOR")
    @casework_blueprint.arguments(AdminCaseQuerySchema, location="query")
    @casework_blueprint.response(200, CaseListEnvelopeSchema)
    def get(self, query: dict[str, Any]) -> dict[str, Any]:
        cases, total = list_cases(query)
        page = query["page"]
        page_size = query["page_size"]
        return {
            "data": {
                "items": [case_summary(case) for case in cases],
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
            "meta": _meta(),
        }


@casework_blueprint.route("/admin/cases/<uuid:case_id>")
class AdminCaseResource(MethodView):
    @require_roles("ADMIN", "INVESTIGATOR")
    @casework_blueprint.response(200, CaseEnvelopeSchema)
    def get(self, case_id: uuid.UUID) -> Any:
        try:
            return {
                "data": staff_case_projection(get_staff_case(case_id)),
                "meta": _meta(),
            }
        except CaseworkFailure as failure:
            return _failure(failure)


@casework_blueprint.route("/admin/cases/<uuid:case_id>/assign")
class AdminCaseAssignResource(MethodView):
    @require_roles("ADMIN", "INVESTIGATOR")
    @casework_blueprint.arguments(CaseAssignSchema)
    @casework_blueprint.response(200, CaseEnvelopeSchema)
    def post(self, data: dict[str, Any], case_id: uuid.UUID) -> Any:
        try:
            case = assign_case(
                case_id=case_id,
                investigator_id=data["investigator_id"],
                expected_version=data["expected_case_version"],
                actor=g.current_user,
                roles=set(g.current_roles),
            )
            return {"data": case_summary(case), "meta": _meta()}
        except CaseworkFailure as failure:
            return _failure(failure)


@casework_blueprint.route("/admin/cases/<uuid:case_id>/start-review")
class AdminCaseReviewResource(MethodView):
    @require_roles("INVESTIGATOR")
    @casework_blueprint.arguments(CaseVersionSchema)
    @casework_blueprint.response(200, CaseEnvelopeSchema)
    def post(self, data: dict[str, Any], case_id: uuid.UUID) -> Any:
        try:
            case = start_review(
                case_id=case_id,
                expected_version=data["expected_case_version"],
                actor=g.current_user,
                roles=set(g.current_roles),
            )
            return {"data": case_summary(case), "meta": _meta()}
        except CaseworkFailure as failure:
            return _failure(failure)


@casework_blueprint.route("/admin/cases/<uuid:case_id>/notes")
class AdminCaseNoteResource(MethodView):
    @require_roles("INVESTIGATOR")
    @casework_blueprint.arguments(CaseNoteSchema)
    @casework_blueprint.response(200, CaseEnvelopeSchema)
    def post(self, data: dict[str, Any], case_id: uuid.UUID) -> Any:
        try:
            case = add_note(
                case_id=case_id,
                note=data["note"],
                expected_version=data["expected_case_version"],
                actor=g.current_user,
                roles=set(g.current_roles),
            )
            return {"data": case_summary(case), "meta": _meta()}
        except CaseworkFailure as failure:
            return _failure(failure)


@casework_blueprint.route("/admin/cases/<uuid:case_id>/decisions")
class AdminCaseDecisionResource(MethodView):
    @require_roles("INVESTIGATOR")
    @casework_blueprint.arguments(CaseDecisionCreateSchema)
    @casework_blueprint.response(200, CaseEnvelopeSchema)
    def post(self, data: dict[str, Any], case_id: uuid.UUID) -> Any:
        try:
            case, decision = record_decision(
                case_id=case_id,
                outcome=data["outcome"],
                reason=data["reason"],
                expected_version=data["expected_case_version"],
                actor=g.current_user,
                roles=set(g.current_roles),
            )
            return {
                "data": {
                    **case_summary(case),
                    "decision": {
                        "id": decision.id,
                        "outcome": decision.outcome,
                        "reason": decision.reason,
                    },
                },
                "meta": _meta(),
            }
        except CaseworkFailure as failure:
            return _failure(failure)


__all__ = ["casework_blueprint"]
