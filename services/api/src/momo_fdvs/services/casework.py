"""Fraud-case creation, projections and optimistic state transitions."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from flask import current_app
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from momo_fdvs.extensions import db
from momo_fdvs.models import (
    AnalysisRun,
    CaseDecision,
    CaseEvent,
    FraudCase,
    IdempotencyRecord,
    Transaction,
    User,
    UserRole,
)
from momo_fdvs.services.audit import audit_event
from momo_fdvs.services.notifications import create_notification

ACTIVE_CASE_STATUSES = ("OPEN", "ASSIGNED", "IN_REVIEW", "REOPENED")
CASE_CATEGORIES = (
    "PAYMENT_NOT_RECEIVED",
    "UNKNOWN_TRANSACTION",
    "ALTERED_RECEIPT",
    "OTHER",
)


@dataclass(frozen=True)
class CaseworkFailure(Exception):
    code: str
    message: str
    status: int


@dataclass(frozen=True)
class CaseCreationResult:
    case: FraudCase
    replayed: bool
    linked_existing: bool


def _payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _claim_idempotency(
    *, user: User, scope: str, key: str, payload_hash: str
) -> tuple[IdempotencyRecord, bool]:
    if not 8 <= len(key) <= 200:
        raise CaseworkFailure(
            "IDEMPOTENCY_KEY_INVALID",
            "Idempotency-Key must contain 8 to 200 characters.",
            400,
        )
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    existing = db.session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.principal_id == user.id,
            IdempotencyRecord.scope == scope,
            IdempotencyRecord.key_hash == key_hash,
        )
    )
    if existing is not None:
        if existing.request_hash != payload_hash:
            raise CaseworkFailure(
                "IDEMPOTENCY_KEY_REUSED",
                "The idempotency key was already used for a different request.",
                409,
            )
        return existing, False
    record = IdempotencyRecord(
        principal_id=user.id,
        scope=scope,
        key_hash=key_hash,
        request_hash=payload_hash,
        expires_at=datetime.now(UTC)
        + timedelta(hours=int(current_app.config["UPLOAD_IDEMPOTENCY_TTL_HOURS"])),
    )
    try:
        with db.session.begin_nested():
            db.session.add(record)
            db.session.flush()
        return record, True
    except IntegrityError as error:
        existing = db.session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.principal_id == user.id,
                IdempotencyRecord.scope == scope,
                IdempotencyRecord.key_hash == key_hash,
            )
        )
        if existing is None:
            raise
        if existing.request_hash != payload_hash:
            raise CaseworkFailure(
                "IDEMPOTENCY_KEY_REUSED",
                "The idempotency key was already used for a different request.",
                409,
            ) from error
        return existing, False


def _active_case(transaction_id: uuid.UUID) -> FraudCase | None:
    return db.session.scalar(
        select(FraudCase)
        .where(
            FraudCase.transaction_id == transaction_id,
            FraudCase.status.in_(ACTIVE_CASE_STATUSES),
        )
        .order_by(FraudCase.opened_at, FraudCase.id)
        .limit(1)
    )


def _require_case(case_id: uuid.UUID) -> FraudCase:
    case = db.session.scalar(
        select(FraudCase)
        .options(selectinload(FraudCase.events), selectinload(FraudCase.decisions))
        .where(FraudCase.id == case_id)
    )
    if case is None:
        raise CaseworkFailure("CASE_NOT_FOUND", "Case not found.", 404)
    return case


def _check_version(case: FraudCase, expected: int) -> None:
    if case.version != expected:
        raise CaseworkFailure(
            "CASE_VERSION_CONFLICT",
            "The case changed since it was loaded. Refresh and try again.",
            409,
        )


def _owner_id(case: FraudCase) -> uuid.UUID:
    transaction = db.session.get(Transaction, case.transaction_id)
    if transaction is None:
        raise CaseworkFailure("CASE_NOT_FOUND", "Case not found.", 404)
    return transaction.user_id


def _event_projection(event: CaseEvent, *, owner_safe: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": event.id,
        "event_type": event.event_type,
        "from_status": event.from_status,
        "to_status": event.to_status,
        "created_at": event.created_at,
    }
    if not owner_safe:
        result["actor_id"] = event.actor_id
        result["reason"] = event.reason
    return result


def case_summary(case: FraudCase) -> dict[str, Any]:
    return {
        "id": case.id,
        "transaction_id": case.transaction_id,
        "source": case.source,
        "category": case.category,
        "status": case.status,
        "version": case.version,
        "opened_at": case.opened_at,
        "updated_at": case.updated_at,
    }


def owner_case_projection(case: FraudCase) -> dict[str, Any]:
    events = sorted(case.events, key=lambda event: (event.created_at, str(event.id)))
    public_events = [
        _event_projection(event, owner_safe=True)
        for event in events
        if event.event_type in {"OPENED", "STATUS", "DECISION", "REOPENED"}
    ]
    return {**case_summary(case), "timeline": public_events}


def _automated_evidence(case: FraudCase) -> dict[str, Any]:
    transaction = db.session.get(Transaction, case.transaction_id)
    run = (
        db.session.get(AnalysisRun, transaction.latest_analysis_run_id)
        if transaction is not None and transaction.latest_analysis_run_id is not None
        else None
    )
    policy = run.component_scores.get("policy", {}) if run is not None else {}
    return {
        "immutable": True,
        "analysis_run_id": run.id if run is not None else None,
        "status": run.status if run is not None else "UNAVAILABLE",
        "risk_band": policy.get("band", "inconclusive")
        if isinstance(policy, dict)
        else "inconclusive",
        "risk_class": run.risk_class if run is not None else None,
    }


def staff_case_projection(case: FraudCase) -> dict[str, Any]:
    events = sorted(case.events, key=lambda event: (event.created_at, str(event.id)))
    decisions = sorted(case.decisions, key=lambda decision: (decision.created_at, str(decision.id)))
    return {
        **case_summary(case),
        "assigned_to": case.assigned_to,
        "description": case.description,
        "automated_evidence": _automated_evidence(case),
        "timeline": [_event_projection(event, owner_safe=False) for event in events],
        "decisions": [
            {
                "id": decision.id,
                "outcome": decision.outcome,
                "reason": decision.reason,
                "decided_by": decision.decided_by,
                "created_at": decision.created_at,
            }
            for decision in decisions
        ],
    }


def create_or_link_owner_case(
    *,
    transaction_id: uuid.UUID,
    category: str,
    description: str | None,
    user: User,
    roles: set[str],
    idempotency_key: str,
) -> CaseCreationResult:
    transaction = db.session.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user.id,
        )
    )
    if transaction is None:
        raise CaseworkFailure("TRANSACTION_NOT_FOUND", "Transaction not found.", 404)
    if transaction.latest_analysis_run_id is None or transaction.status not in {
        "COMPLETED",
        "PARTIAL",
    }:
        raise CaseworkFailure(
            "ANALYSIS_REQUIRED",
            "A completed or partial analysis is required before reporting this transaction.",
            409,
        )
    normalized_description = description.strip() if description else None
    digest = _payload_hash(
        {
            "transaction_id": str(transaction.id),
            "category": category,
            "description": normalized_description,
        }
    )
    record, claimed = _claim_idempotency(
        user=user,
        scope=f"POST:/api/v1/transactions/{transaction.id}/fraud-reports",
        key=idempotency_key,
        payload_hash=digest,
    )
    if not claimed:
        if record.resource_id is None:
            raise CaseworkFailure(
                "IDEMPOTENCY_REQUEST_IN_PROGRESS",
                "The original case request is still in progress.",
                409,
            )
        replayed_case = db.session.get(FraudCase, record.resource_id)
        if replayed_case is None:
            raise CaseworkFailure(
                "IDEMPOTENCY_RESOURCE_UNAVAILABLE",
                "The original case is unavailable.",
                409,
            )
        return CaseCreationResult(replayed_case, replayed=True, linked_existing=False)

    existing = _active_case(transaction.id)
    linked_existing = existing is not None
    case = existing
    if case is None:
        case = FraudCase(
            transaction_id=transaction.id,
            source="USER_REPORT",
            reporter_id=user.id,
            category=category,
            description=normalized_description,
            status="OPEN",
            version=1,
            opened_at=datetime.now(UTC),
        )
        try:
            with db.session.begin_nested():
                db.session.add(case)
                db.session.flush()
        except IntegrityError:
            case = _active_case(transaction.id)
            if case is None:
                raise
            linked_existing = True

    if not linked_existing:
        db.session.add(
            CaseEvent(
                case_id=case.id,
                actor_id=user.id,
                event_type="OPENED",
                to_status="OPEN",
                reason=None,
                metadata_json={"source": "USER_REPORT"},
            )
        )
        create_notification(
            user_id=user.id,
            notification_type="CASE_OPENED",
            title="Fraud report received",
            message="Your report has been opened for review.",
            dedupe_key=f"case:{case.id}:opened",
            target_type="CASE",
            target_id=case.id,
        )
        audit_event(
            "case.opened",
            "SUCCESS",
            actor_id=user.id,
            roles=roles,
            target_type="fraud_case",
            target_id=case.id,
            metadata={"source": "USER_REPORT", "category": category},
        )
    else:
        audit_event(
            "case.existing_linked",
            "SUCCESS",
            actor_id=user.id,
            roles=roles,
            target_type="fraud_case",
            target_id=case.id,
            metadata={"source": case.source},
        )
    record.resource_type = "fraud_case"
    record.resource_id = case.id
    record.response_status = 200 if linked_existing else 201
    db.session.commit()
    return CaseCreationResult(case, replayed=False, linked_existing=linked_existing)


def get_owner_case(case_id: uuid.UUID, user_id: uuid.UUID) -> FraudCase:
    case = db.session.scalar(
        select(FraudCase)
        .options(selectinload(FraudCase.events))
        .join(Transaction, Transaction.id == FraudCase.transaction_id)
        .where(
            FraudCase.id == case_id,
            Transaction.user_id == user_id,
        )
    )
    if case is None:
        raise CaseworkFailure("CASE_NOT_FOUND", "Case not found.", 404)
    return case


def list_cases(filters: dict[str, Any]) -> tuple[list[FraudCase], int]:
    statement = select(FraudCase).options(selectinload(FraudCase.events))
    count_statement = select(func.count(FraudCase.id))
    if status := filters.get("status"):
        statement = statement.where(FraudCase.status == status)
        count_statement = count_statement.where(FraudCase.status == status)
    if source := filters.get("source"):
        statement = statement.where(FraudCase.source == source)
        count_statement = count_statement.where(FraudCase.source == source)
    if assigned_to := filters.get("assigned_to"):
        statement = statement.where(FraudCase.assigned_to == assigned_to)
        count_statement = count_statement.where(FraudCase.assigned_to == assigned_to)
    page = filters["page"]
    page_size = filters["page_size"]
    cases = list(
        db.session.scalars(
            statement.order_by(FraudCase.opened_at.desc(), FraudCase.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return cases, int(db.session.scalar(count_statement) or 0)


def get_staff_case(case_id: uuid.UUID) -> FraudCase:
    return _require_case(case_id)


def _record_case_notification(case: FraudCase, notification_type: str, message: str) -> None:
    create_notification(
        user_id=_owner_id(case),
        notification_type=notification_type,
        title="Fraud report updated",
        message=message,
        dedupe_key=f"case:{case.id}:version:{case.version}:{notification_type}",
        target_type="CASE",
        target_id=case.id,
    )


def assign_case(
    *,
    case_id: uuid.UUID,
    investigator_id: uuid.UUID,
    expected_version: int,
    actor: User,
    roles: set[str],
) -> FraudCase:
    case = _require_case(case_id)
    _check_version(case, expected_version)
    if case.status not in {"OPEN", "ASSIGNED", "REOPENED"}:
        raise CaseworkFailure(
            "CASE_TRANSITION_INVALID", "This case cannot be assigned in its current state.", 409
        )
    investigator = db.session.get(User, investigator_id)
    has_role = db.session.scalar(
        select(UserRole.user_id).where(
            UserRole.user_id == investigator_id,
            UserRole.role_code == "INVESTIGATOR",
        )
    )
    if investigator is None or investigator.status != "ACTIVE" or has_role is None:
        raise CaseworkFailure(
            "INVESTIGATOR_INVALID", "The selected investigator is not active.", 422
        )
    previous = case.status
    case.assigned_to = investigator_id
    case.status = "ASSIGNED"
    case.version += 1
    db.session.add(
        CaseEvent(
            case_id=case.id,
            actor_id=actor.id,
            event_type="ASSIGNED",
            from_status=previous,
            to_status="ASSIGNED",
            metadata_json={},
        )
    )
    _record_case_notification(case, "CASE_ASSIGNED", "Your report was assigned for review.")
    create_notification(
        user_id=investigator_id,
        notification_type="CASE_ASSIGNED_TO_YOU",
        title="Case assigned",
        message="A case was assigned to your review queue.",
        dedupe_key=f"case:{case.id}:version:{case.version}:assignee",
        target_type="CASE",
        target_id=case.id,
    )
    audit_event(
        "case.assigned",
        "SUCCESS",
        actor_id=actor.id,
        roles=roles,
        target_type="fraud_case",
        target_id=case.id,
        metadata={"case_version": case.version},
    )
    db.session.commit()
    return case


def start_review(
    *, case_id: uuid.UUID, expected_version: int, actor: User, roles: set[str]
) -> FraudCase:
    case = _require_case(case_id)
    _check_version(case, expected_version)
    if case.status not in {"OPEN", "ASSIGNED", "REOPENED"}:
        raise CaseworkFailure(
            "CASE_TRANSITION_INVALID", "This case cannot enter review from its current state.", 409
        )
    if case.assigned_to not in {None, actor.id}:
        raise CaseworkFailure(
            "CASE_ASSIGNED_TO_ANOTHER_INVESTIGATOR",
            "This case is assigned to another investigator.",
            409,
        )
    previous = case.status
    case.assigned_to = actor.id
    case.status = "IN_REVIEW"
    case.version += 1
    db.session.add(
        CaseEvent(
            case_id=case.id,
            actor_id=actor.id,
            event_type="STATUS",
            from_status=previous,
            to_status="IN_REVIEW",
            metadata_json={},
        )
    )
    _record_case_notification(case, "CASE_IN_REVIEW", "Your report is now under review.")
    audit_event(
        "case.review_started",
        "SUCCESS",
        actor_id=actor.id,
        roles=roles,
        target_type="fraud_case",
        target_id=case.id,
        metadata={"case_version": case.version},
    )
    db.session.commit()
    return case


def add_note(
    *,
    case_id: uuid.UUID,
    note: str,
    expected_version: int,
    actor: User,
    roles: set[str],
) -> FraudCase:
    case = _require_case(case_id)
    _check_version(case, expected_version)
    if case.status not in {"ASSIGNED", "IN_REVIEW", "REOPENED"}:
        raise CaseworkFailure(
            "CASE_TRANSITION_INVALID", "Notes cannot be added in the current case state.", 409
        )
    if case.assigned_to not in {None, actor.id}:
        raise CaseworkFailure(
            "CASE_ASSIGNED_TO_ANOTHER_INVESTIGATOR",
            "This case is assigned to another investigator.",
            409,
        )
    case.version += 1
    db.session.add(
        CaseEvent(
            case_id=case.id,
            actor_id=actor.id,
            event_type="NOTE",
            from_status=case.status,
            to_status=case.status,
            reason=note.strip(),
            metadata_json={},
        )
    )
    audit_event(
        "case.note_added",
        "SUCCESS",
        actor_id=actor.id,
        roles=roles,
        target_type="fraud_case",
        target_id=case.id,
        metadata={"case_version": case.version},
    )
    db.session.commit()
    return case


def record_decision(
    *,
    case_id: uuid.UUID,
    outcome: str,
    reason: str,
    expected_version: int,
    actor: User,
    roles: set[str],
) -> tuple[FraudCase, CaseDecision]:
    case = _require_case(case_id)
    _check_version(case, expected_version)
    if case.status != "IN_REVIEW" or case.assigned_to != actor.id:
        raise CaseworkFailure(
            "CASE_TRANSITION_INVALID", "Only the assigned case under review can be decided.", 409
        )
    previous = case.status
    case.status = "DECIDED"
    case.version += 1
    decision = CaseDecision(
        case_id=case.id,
        decided_by=actor.id,
        outcome=outcome,
        reason=reason.strip(),
    )
    db.session.add(decision)
    db.session.flush()
    db.session.add(
        CaseEvent(
            case_id=case.id,
            actor_id=actor.id,
            event_type="DECISION",
            from_status=previous,
            to_status="DECIDED",
            reason=reason.strip(),
            metadata_json={"outcome": outcome, "decision_id": str(decision.id)},
        )
    )
    _record_case_notification(case, "CASE_DECIDED", "A decision was recorded for your report.")
    audit_event(
        "case.decision_recorded",
        "SUCCESS",
        actor_id=actor.id,
        roles=roles,
        target_type="fraud_case",
        target_id=case.id,
        metadata={"case_version": case.version, "outcome": outcome},
    )
    db.session.commit()
    return case, decision


__all__ = [
    "CASE_CATEGORIES",
    "CaseCreationResult",
    "CaseworkFailure",
    "add_note",
    "assign_case",
    "case_summary",
    "create_or_link_owner_case",
    "get_owner_case",
    "get_staff_case",
    "list_cases",
    "owner_case_projection",
    "record_decision",
    "staff_case_projection",
    "start_review",
]
