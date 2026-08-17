"""Owner-safe immutable HTML analysis report generation."""

from __future__ import annotations

import hashlib
import html
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from flask import current_app
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from momo_fdvs.api.v1.analyses import risk_projection
from momo_fdvs.extensions import db
from momo_fdvs.models import (
    AnalysisRun,
    FraudCase,
    IdempotencyRecord,
    OCRConfirmation,
    ReportArtifact,
    Transaction,
    User,
    VerificationResult,
)
from momo_fdvs.services.audit import audit_event
from momo_fdvs.services.verification import verification_projection
from momo_fdvs.storage.base import ObjectStorage, generated_key, sha256_bytes


@dataclass(frozen=True)
class ReportFailure(Exception):
    code: str
    message: str
    status: int


@dataclass(frozen=True)
class ReportCreationResult:
    artifact: ReportArtifact
    replayed: bool


def _safe(value: object) -> str:
    return html.escape(str(value), quote=True)


def _payload_hash(transaction_id: uuid.UUID, report_format: str) -> str:
    raw = json.dumps(
        {"transaction_id": str(transaction_id), "format": report_format},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _claim_report_key(
    *, user: User, transaction_id: uuid.UUID, key: str, report_format: str
) -> tuple[IdempotencyRecord, bool]:
    if not 8 <= len(key) <= 200:
        raise ReportFailure(
            "IDEMPOTENCY_KEY_INVALID",
            "Idempotency-Key must contain 8 to 200 characters.",
            400,
        )
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    request_hash = _payload_hash(transaction_id, report_format)
    scope = f"analysis-report:{transaction_id}"
    record = db.session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.principal_id == user.id,
            IdempotencyRecord.scope == scope,
            IdempotencyRecord.key_hash == key_hash,
        )
    )
    if record is not None:
        if record.request_hash != request_hash:
            raise ReportFailure(
                "IDEMPOTENCY_KEY_REUSED",
                "The idempotency key was already used for a different request.",
                409,
            )
        return record, False
    record = IdempotencyRecord(
        principal_id=user.id,
        scope=scope,
        key_hash=key_hash,
        request_hash=request_hash,
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
        if existing.request_hash != request_hash:
            raise ReportFailure(
                "IDEMPOTENCY_KEY_REUSED",
                "The idempotency key was already used for a different request.",
                409,
            ) from error
        return existing, False


def _analysis_context(
    user_id: uuid.UUID, transaction_id: uuid.UUID
) -> tuple[Transaction, AnalysisRun, OCRConfirmation | None, VerificationResult | None]:
    transaction = db.session.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
    )
    if transaction is None:
        raise ReportFailure("TRANSACTION_NOT_FOUND", "Transaction not found.", 404)
    if transaction.latest_analysis_run_id is None:
        raise ReportFailure(
            "ANALYSIS_REQUIRED",
            "A completed or partial analysis is required before generating a report.",
            409,
        )
    run = db.session.get(AnalysisRun, transaction.latest_analysis_run_id)
    if run is None or run.status not in {"COMPLETED", "PARTIAL"}:
        raise ReportFailure(
            "ANALYSIS_REQUIRED",
            "A completed or partial analysis is required before generating a report.",
            409,
        )
    confirmation = (
        db.session.get(OCRConfirmation, run.ocr_confirmation_id)
        if run.ocr_confirmation_id is not None
        else None
    )
    if confirmation is None and run.analysis_mode != "screenshot_only":
        raise ReportFailure("REPORT_UNAVAILABLE", "The report cannot be generated.", 503)
    verification = db.session.scalar(
        select(VerificationResult).where(VerificationResult.analysis_run_id == run.id)
    )
    return transaction, run, confirmation, verification


def _list(values: object) -> str:
    if not isinstance(values, list) or not values:
        return "<li>None recorded.</li>"
    items: list[str] = []
    for item in values:
        if isinstance(item, dict):
            text = item.get("title") or item.get("code") or "Recorded reason"
        else:
            text = item
        items.append(f"<li>{_safe(text)}</li>")
    return "".join(items)


def render_analysis_report(
    transaction: Transaction,
    run: AnalysisRun,
    confirmation: OCRConfirmation | None,
    verification: VerificationResult | None,
    *,
    generated_at: datetime,
) -> bytes:
    """Render a standalone escaped report without raw receipt or OCR values."""
    risk = risk_projection(run)
    verification_data = (
        verification_projection(verification)
        if verification is not None
        else {
            "label": "Unavailable",
            "status": "UNVERIFIED",
            "summary": "No stored-reference verification result is available.",
            "disclaimer": "This is not a live confirmation from a mobile-money provider.",
        }
    )
    components = run.component_scores if isinstance(run.component_scores, dict) else {}
    component_rows = "".join(
        f"<tr><th>{_safe(name.replace('_', ' ').title())}</th>"
        "<td>"
        f"{_safe((value if isinstance(value, dict) else {}).get('status', 'UNAVAILABLE'))}"
        "</td></tr>"
        for name, value in components.items()
        if name != "policy"
    )
    versions = run.configuration_snapshot if isinstance(run.configuration_snapshot, dict) else {}
    version_rows = "".join(
        f"<tr><th>{_safe(name.replace('_', ' ').title())}</th><td>{_safe(value)}</td></tr>"
        for name, value in versions.items()
        if name.endswith("_version") and value is not None
    )
    component_table = component_rows or "<tr><td>No component status recorded.</td></tr>"
    version_table = version_rows or "<tr><td>No version identity recorded.</td></tr>"
    degraded_note = (
        "<p>Some optional evidence components were unavailable. The recorded fraud-risk "
        "conclusion remains based on the available evidence.</p>"
        if risk["component_status"] == "DEGRADED" and risk["conclusion_status"] == "CONCLUSIVE"
        else ""
    )
    analysis_mode = str(getattr(run, "analysis_mode", "combined"))
    confirmed_field_count: int | str = (
        len(confirmation.confirmed_fields) if confirmation is not None else "Not applicable"
    )
    verification_limitation = (
        "No transaction verification was attempted for this screenshot-only analysis."
        if analysis_mode == "screenshot_only"
        else (
            "Verification uses stored or imported reference transactions. It is not a live "
            "confirmation from a mobile-money provider."
        )
    )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>MoMo-FDVS analysis report</title>
<style>body{{font-family:system-ui,sans-serif;max-width:800px;margin:2rem auto;
padding:0 1rem;color:#17202a}}
h1,h2{{color:#173b57}}section{{border:1px solid #d8e0e7;border-radius:10px;
padding:1rem;margin:1rem 0}}
table{{border-collapse:collapse;width:100%}}th,td{{text-align:left;padding:.45rem;
border-bottom:1px solid #e8edf1}}
.notice{{background:#fff7df}}small{{color:#536471}}</style></head><body>
<h1>MoMo-FDVS analysis report</h1>
<p><small>Generated {_safe(generated_at.isoformat())}. Automated evidence is immutable.</small></p>
<section><h2>Transaction</h2><table>
<tr><th>Provider</th><td>{_safe(transaction.provider_code or "Not recorded")}</td></tr>
<tr><th>Reference</th><td>{_safe(transaction.display_reference_masked or "Masked")}</td></tr>
<tr><th>Analysis mode</th><td>{_safe(analysis_mode.replace("_", " ").title())}</td></tr>
<tr><th>Confirmed OCR fields</th><td>{confirmed_field_count}</td></tr>
</table></section>
<section><h2>Fraud-risk assessment</h2><table>
<tr><th>Risk band</th><td>{_safe(risk["band"])}</td></tr>
<tr><th>Conclusion</th><td>{_safe(str(risk["conclusion_status"]).title())}</td></tr>
<tr><th>Component availability</th><td>{_safe(str(risk["component_status"]).title())}</td></tr>
</table>
<p>{_safe(risk["summary"])}</p>{degraded_note}
<h3>Reasons</h3><ul>{_list(risk["reasons"])}</ul>
<h3>Limitations</h3><ul>{_list(risk["limitations"])}</ul>
<p>{_safe(risk["disclaimer"])}</p></section>
<section><h2>Transaction verification</h2>
<p><strong>{_safe(verification_data["label"])}</strong> — {_safe(verification_data["summary"])}</p>
<p>{_safe(verification_data["disclaimer"])}</p></section>
<section><h2>Component availability</h2><table>{component_table}</table></section>
<section><h2>Evidence versions</h2><table>{version_table}</table></section>
<section class="notice"><h2>Important limitation</h2>
<p>{verification_limitation}</p>
<p>This report supports review and does not by itself prove fraud or complete a legal
determination.</p></section>
</body></html>"""
    return document.encode("utf-8")


def report_projection(artifact: ReportArtifact, *, replayed: bool = False) -> dict[str, Any]:
    download_url = None
    if artifact.status == "READY" and artifact.report_type == "ANALYSIS":
        download_url = f"/api/v1/reports/{artifact.id}/download"
    elif artifact.status == "READY" and artifact.report_type == "CASE" and artifact.case_id:
        download_url = f"/api/v1/admin/cases/{artifact.case_id}/reports/{artifact.id}/download"
    return {
        "id": artifact.id,
        "report_type": artifact.report_type,
        "transaction_id": artifact.transaction_id,
        "analysis_run_id": artifact.analysis_run_id,
        "status": artifact.status,
        "sha256": artifact.sha256,
        "generated_at": artifact.generated_at,
        "expires_at": artifact.expires_at,
        "download_url": download_url,
        "replayed": replayed,
    }


def create_analysis_report(
    *,
    user: User,
    roles: set[str],
    transaction_id: uuid.UUID,
    idempotency_key: str,
    report_format: str,
    storage: ObjectStorage,
) -> ReportCreationResult:
    if report_format != "HTML":
        raise ReportFailure("REPORT_FORMAT_UNSUPPORTED", "Only HTML reports are supported.", 400)
    transaction, run, confirmation, verification = _analysis_context(user.id, transaction_id)
    record, claimed = _claim_report_key(
        user=user,
        transaction_id=transaction_id,
        key=idempotency_key,
        report_format=report_format,
    )
    if not claimed and record.resource_id is not None:
        existing = db.session.get(ReportArtifact, record.resource_id)
        if existing is not None and existing.owner_user_id == user.id:
            if existing.status == "READY":
                return ReportCreationResult(existing, True)
            raise ReportFailure("REPORT_UNAVAILABLE", "The report is not available.", 503)

    artifact = ReportArtifact(
        report_type="ANALYSIS",
        owner_user_id=user.id,
        transaction_id=transaction.id,
        analysis_run_id=run.id,
        source_version=1,
        object_key=generated_key("reports/analysis", "html"),
        status="GENERATING",
        generated_by=user.id,
    )
    db.session.add(artifact)
    db.session.flush()
    record.resource_type = "report_artifact"
    record.resource_id = artifact.id
    record.response_status = 201
    db.session.commit()

    object_key = artifact.object_key
    try:
        generated_at = datetime.now(UTC)
        content = render_analysis_report(
            transaction,
            run,
            confirmation,
            verification,
            generated_at=generated_at,
        )
        stored = storage.put_bytes(
            object_key,
            content,
            "text/html; charset=utf-8",
            {"classification": "private-analysis-report", "report-id": str(artifact.id)},
        )
        read_back = storage.read_bytes(object_key)
        digest = sha256_bytes(read_back)
        if read_back != content or digest != stored.sha256:
            raise OSError("stored report integrity check failed")
        artifact.sha256 = digest
        artifact.status = "READY"
        artifact.generated_at = generated_at
        audit_event(
            "report.generated",
            "SUCCESS",
            actor_id=user.id,
            roles=roles,
            target_type="report_artifact",
            target_id=artifact.id,
            metadata={"report_type": "ANALYSIS"},
        )
        db.session.commit()
        return ReportCreationResult(artifact, False)
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("analysis_report_generation_failed", exc_info=exc)
        try:
            if storage.exists(object_key):
                storage.delete(object_key)
        except Exception:
            current_app.logger.exception("analysis_report_cleanup_failed")
        failed = db.session.get(ReportArtifact, artifact.id)
        if failed is not None:
            failed.status = "FAILED"
            audit_event(
                "report.generation_failed",
                "FAILURE",
                actor_id=user.id,
                roles=roles,
                target_type="report_artifact",
                target_id=failed.id,
                metadata={"report_type": "ANALYSIS"},
            )
            db.session.commit()
        raise ReportFailure(
            "REPORT_STORAGE_UNAVAILABLE",
            "The report could not be generated. Try again later.",
            503,
        ) from None


def owned_ready_report(user_id: uuid.UUID, report_id: uuid.UUID) -> ReportArtifact | None:
    return db.session.scalar(
        select(ReportArtifact).where(
            ReportArtifact.id == report_id,
            ReportArtifact.owner_user_id == user_id,
            ReportArtifact.status == "READY",
        )
    )


def _claim_case_report_key(
    *, user: User, case: FraudCase, key: str
) -> tuple[IdempotencyRecord, bool]:
    if not 8 <= len(key) <= 200:
        raise ReportFailure(
            "IDEMPOTENCY_KEY_INVALID",
            "Idempotency-Key must contain 8 to 200 characters.",
            400,
        )
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    request_hash = hashlib.sha256(f"{case.id}:{case.version}:HTML".encode()).hexdigest()
    scope = f"case-report:{case.id}"
    existing = db.session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.principal_id == user.id,
            IdempotencyRecord.scope == scope,
            IdempotencyRecord.key_hash == key_hash,
        )
    )
    if existing is not None:
        if existing.request_hash != request_hash:
            raise ReportFailure(
                "IDEMPOTENCY_KEY_REUSED",
                "The idempotency key was already used for a different case version.",
                409,
            )
        return existing, False
    record = IdempotencyRecord(
        principal_id=user.id,
        scope=scope,
        key_hash=key_hash,
        request_hash=request_hash,
        expires_at=datetime.now(UTC)
        + timedelta(hours=int(current_app.config["UPLOAD_IDEMPOTENCY_TTL_HOURS"])),
    )
    try:
        with db.session.begin_nested():
            db.session.add(record)
            db.session.flush()
        return record, True
    except IntegrityError:
        raced = db.session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.principal_id == user.id,
                IdempotencyRecord.scope == scope,
                IdempotencyRecord.key_hash == key_hash,
            )
        )
        if raced is None:
            raise
        return raced, False


def render_case_report(case: FraudCase, *, generated_at: datetime) -> bytes:
    transaction = db.session.get(Transaction, case.transaction_id)
    run = (
        db.session.get(AnalysisRun, transaction.latest_analysis_run_id)
        if transaction is not None and transaction.latest_analysis_run_id is not None
        else None
    )
    policy = (
        run.component_scores.get("policy", {})
        if run is not None and isinstance(run.component_scores, dict)
        else {}
    )
    risk_band = policy.get("band", "inconclusive") if isinstance(policy, dict) else "inconclusive"
    events = sorted(case.events, key=lambda event: (event.created_at, str(event.id)))
    event_rows = "".join(
        "<tr>"
        f"<td>{_safe(event.created_at.isoformat())}</td>"
        f"<td>{_safe(event.event_type)}</td>"
        f"<td>{_safe(event.to_status or event.from_status or 'Recorded')}</td>"
        f"<td>{_safe(event.reason or 'No public reason recorded')}</td>"
        "</tr>"
        for event in events
    )
    decision = max(case.decisions, key=lambda item: item.created_at, default=None)
    masked_reference = transaction.display_reference_masked if transaction else "Unavailable"
    analysis_status = run.status if run else "Unavailable"
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>MoMo-FDVS case report</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}
section{{border:1px solid #d8e0e7;border-radius:10px;padding:1rem;margin:1rem 0}}
table{{border-collapse:collapse;width:100%}}th,td{{text-align:left;padding:.45rem;
border-bottom:1px solid #e8edf1}}</style></head><body>
<h1>MoMo-FDVS investigation case report</h1>
<p>Generated {_safe(generated_at.isoformat())}. Case version {_safe(case.version)}.</p>
<section><h2>Case</h2><p>Status: <strong>{_safe(case.status)}</strong></p>
<p>Category: {_safe(case.category)}</p><p>Source: {_safe(case.source)}</p>
<p>Masked reference: {_safe(masked_reference)}</p></section>
<section><h2>Automated evidence</h2><p>Analysis status: {_safe(analysis_status)}</p>
<p>Fraud-risk band: {_safe(risk_band)}</p>
<p>Automated evidence is immutable. Human review did not rewrite the model or policy
output.</p></section>
<section><h2>Human decision</h2><p>Outcome: {_safe(decision.outcome if decision else "Pending")}</p>
<p>Reason: {_safe(decision.reason if decision else "No decision recorded")}</p></section>
<section><h2>Append-only timeline</h2><table><thead><tr><th>Time</th><th>Event</th>
<th>Status</th><th>Reason</th></tr></thead><tbody>{event_rows}</tbody></table></section>
<section><h2>Important limitation</h2><p>Transaction verification uses stored or imported reference
transactions. It is not a live confirmation from a mobile-money provider.</p></section>
</body></html>"""
    return document.encode("utf-8")


def create_case_report(
    *,
    case_id: uuid.UUID,
    user: User,
    roles: set[str],
    idempotency_key: str,
    storage: ObjectStorage,
) -> ReportCreationResult:
    case = db.session.get(FraudCase, case_id)
    if case is None:
        raise ReportFailure("CASE_NOT_FOUND", "Case not found.", 404)
    record, claimed = _claim_case_report_key(user=user, case=case, key=idempotency_key)
    if not claimed and record.resource_id is not None:
        existing = db.session.get(ReportArtifact, record.resource_id)
        if existing is not None and existing.case_id == case.id and existing.status == "READY":
            return ReportCreationResult(existing, True)
        raise ReportFailure("REPORT_UNAVAILABLE", "The report is not available.", 503)
    artifact = ReportArtifact(
        report_type="CASE",
        case_id=case.id,
        source_version=case.version,
        object_key=generated_key("reports/case", "html"),
        status="GENERATING",
        generated_by=user.id,
    )
    db.session.add(artifact)
    db.session.flush()
    record.resource_type = "report_artifact"
    record.resource_id = artifact.id
    record.response_status = 201
    db.session.commit()
    object_key = artifact.object_key
    try:
        generated_at = datetime.now(UTC)
        content = render_case_report(case, generated_at=generated_at)
        stored = storage.put_bytes(
            object_key,
            content,
            "text/html; charset=utf-8",
            {"classification": "private-case-report", "report-id": str(artifact.id)},
        )
        read_back = storage.read_bytes(object_key)
        digest = sha256_bytes(read_back)
        if read_back != content or digest != stored.sha256:
            raise OSError("stored report integrity check failed")
        artifact.sha256 = digest
        artifact.status = "READY"
        artifact.generated_at = generated_at
        audit_event(
            "case.report_generated",
            "SUCCESS",
            actor_id=user.id,
            roles=roles,
            target_type="report_artifact",
            target_id=artifact.id,
            metadata={"case_version": case.version},
        )
        db.session.commit()
        return ReportCreationResult(artifact, False)
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("case_report_generation_failed", exc_info=exc)
        try:
            if storage.exists(object_key):
                storage.delete(object_key)
        except Exception:
            current_app.logger.exception("case_report_cleanup_failed")
        failed = db.session.get(ReportArtifact, artifact.id)
        if failed is not None:
            failed.status = "FAILED"
            db.session.commit()
        raise ReportFailure(
            "REPORT_STORAGE_UNAVAILABLE",
            "The report could not be generated. Try again later.",
            503,
        ) from None


def staff_ready_case_report(case_id: uuid.UUID, report_id: uuid.UUID) -> ReportArtifact | None:
    return db.session.scalar(
        select(ReportArtifact).where(
            ReportArtifact.id == report_id,
            ReportArtifact.case_id == case_id,
            ReportArtifact.report_type == "CASE",
            ReportArtifact.status == "READY",
        )
    )


__all__ = [
    "ReportCreationResult",
    "ReportFailure",
    "create_analysis_report",
    "create_case_report",
    "owned_ready_report",
    "render_analysis_report",
    "render_case_report",
    "report_projection",
    "staff_ready_case_report",
]
