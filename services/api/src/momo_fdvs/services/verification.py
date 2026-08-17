"""Private reference imports and versioned stored-record verification."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from difflib import SequenceMatcher
from pathlib import PurePath
from typing import Any

from flask import current_app
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from momo_fdvs.extensions import db
from momo_fdvs.models import (
    AnalysisRun,
    AnalysisStageRun,
    FraudRuleSet,
    IdempotencyRecord,
    ImageAnalysis,
    OCRConfirmation,
    Receipt,
    ReferenceImportBatch,
    ReferenceTransaction,
    Transaction,
    User,
    VerificationResult,
)
from momo_fdvs.services.audit import audit_event
from momo_fdvs.services.image_forensics import (
    ImageForensicsFailure,
    run_image_forensics,
)
from momo_fdvs.services.ocr import (
    normalize_amount,
    normalize_name,
    normalize_occurred_at,
    normalize_phone,
    normalize_reference,
)
from momo_fdvs.storage.base import ObjectStorage, generated_key, sha256_bytes

CSV_COLUMNS = (
    "provider_code",
    "transaction_reference",
    "amount",
    "currency",
    "sender_name",
    "sender_phone",
    "receiver_name",
    "receiver_phone",
    "occurred_at",
    "transaction_status",
    "source_system_id",
)
REQUIRED_COLUMNS = {"provider_code", "transaction_reference", "amount", "currency"}
CRITICAL_FIELDS = {
    "amount",
    "currency",
    "sender_phone",
    "receiver_phone",
    "occurred_at",
    "transaction_status",
}


class VerificationFailure(RuntimeError):
    """A safe reference-import or verification workflow failure."""

    def __init__(
        self,
        code: str,
        message: str,
        status: int,
        field_errors: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.field_errors = field_errors


@dataclass(frozen=True)
class ParsedReferenceRow:
    row_number: int
    canonical: dict[str, Any]
    raw: dict[str, str]


@dataclass(frozen=True)
class ImportValidation:
    total_rows: int
    valid_rows: list[ParsedReferenceRow]
    errors: list[dict[str, Any]]


@dataclass(frozen=True)
class ImportUploadResult:
    batch: ReferenceImportBatch
    replayed: bool


@dataclass(frozen=True)
class VerificationOutcome:
    status: str
    reference: ReferenceTransaction | None
    candidate_method: str
    comparisons: dict[str, dict[str, Any]]
    matched_count: int
    mismatched_count: int
    warnings: list[str]
    verifier_version: str


@dataclass(frozen=True)
class PartialAnalysisResult:
    run: AnalysisRun
    verification: VerificationResult
    image_analysis: ImageAnalysis | None
    image_error_code: str | None
    replayed: bool


def _canonical_provider(value: str) -> str | None:
    candidate = re.sub(r"[^A-Z0-9_]", "_", value.strip().upper()).strip("_")
    return candidate if candidate and len(candidate) <= 50 else None


def _canonical_currency(value: str) -> str | None:
    candidate = value.strip().upper()
    return candidate if re.fullmatch(r"[A-Z]{3}", candidate) else None


def _canonical_status(value: str) -> str | None:
    candidate = " ".join(value.strip().upper().split())
    return candidate if candidate and len(candidate) <= 50 else None


def _clean_csv_filename(filename: str | None) -> str:
    name = PurePath((filename or "reference.csv").replace("\\", "/")).name.strip()
    name = "".join(character for character in name if character.isprintable())[:255]
    if not name.lower().endswith(".csv"):
        raise VerificationFailure(
            "REFERENCE_FILE_TYPE_INVALID", "Reference imports must use a .csv filename.", 415
        )
    return name or "reference.csv"


def _decode_csv(content: bytes) -> str:
    if not content:
        raise VerificationFailure("REFERENCE_FILE_EMPTY", "The CSV file is empty.", 400)
    if len(content) > current_app.config["REFERENCE_IMPORT_MAX_BYTES"]:
        raise VerificationFailure(
            "REFERENCE_FILE_TOO_LARGE", "The CSV file exceeds the configured size limit.", 413
        )
    if b"\x00" in content:
        raise VerificationFailure(
            "REFERENCE_FILE_INVALID", "The CSV file contains unsupported binary content.", 400
        )
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise VerificationFailure(
            "REFERENCE_FILE_ENCODING_INVALID", "The CSV file must use UTF-8 encoding.", 400
        ) from exc


def _row_error(row: int, field: str, code: str, message: str) -> dict[str, Any]:
    return {"row": row, "field": field, "code": code, "message": message}


def parse_reference_csv(content: bytes) -> ImportValidation:
    reader = csv.DictReader(io.StringIO(_decode_csv(content), newline=""))
    original_headers = reader.fieldnames or []
    headers = [header.strip() for header in original_headers if header is not None]
    if len(headers) != len(original_headers) or len(set(headers)) != len(headers):
        raise VerificationFailure(
            "REFERENCE_HEADERS_INVALID",
            "The CSV header contains blank or duplicate columns.",
            422,
        )
    if not headers or not REQUIRED_COLUMNS.issubset(headers):
        missing = sorted(REQUIRED_COLUMNS - set(headers))
        raise VerificationFailure(
            "REFERENCE_HEADERS_INVALID",
            "The CSV header is missing required columns.",
            422,
            {"file": [f"Missing: {', '.join(missing)}"]},
        )
    unknown = sorted(set(headers) - set(CSV_COLUMNS))
    if unknown:
        raise VerificationFailure(
            "REFERENCE_HEADERS_INVALID",
            "The CSV header contains unsupported columns.",
            422,
            {"file": [f"Unsupported: {', '.join(unknown)}"]},
        )
    reader.fieldnames = headers
    maximum_rows = current_app.config["REFERENCE_IMPORT_MAX_ROWS"]
    valid: list[ParsedReferenceRow] = []
    errors: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    total = 0
    for total, raw_row in enumerate(reader, start=1):
        if total > maximum_rows:
            raise VerificationFailure(
                "REFERENCE_ROW_LIMIT_EXCEEDED",
                "The CSV contains more rows than the configured limit.",
                413,
            )
        row_number = total + 1
        raw = {column: (raw_row.get(column) or "").strip() for column in CSV_COLUMNS}
        if raw_row.get(None):
            errors.append(
                _row_error(
                    row_number,
                    "file",
                    "MALFORMED_ROW",
                    "The row contains more values than the CSV header.",
                )
            )
            continue
        provider = _canonical_provider(raw["provider_code"])
        reference = normalize_reference(raw["transaction_reference"])
        amount = normalize_amount(raw["amount"])
        currency = _canonical_currency(raw["currency"])
        occurred_at, date_warnings = normalize_occurred_at(raw["occurred_at"])
        canonical: dict[str, Any] = {
            "provider_code": provider,
            "transaction_reference": reference,
            "amount": amount,
            "currency": currency,
            "sender_name": normalize_name(raw["sender_name"]) if raw["sender_name"] else None,
            "sender_phone": normalize_phone(raw["sender_phone"]) if raw["sender_phone"] else None,
            "receiver_name": normalize_name(raw["receiver_name"]) if raw["receiver_name"] else None,
            "receiver_phone": normalize_phone(raw["receiver_phone"])
            if raw["receiver_phone"]
            else None,
            "occurred_at": occurred_at,
            "transaction_status": _canonical_status(raw["transaction_status"])
            if raw["transaction_status"]
            else None,
            "source_system_id": raw["source_system_id"][:150] or None,
        }
        row_errors: list[dict[str, Any]] = []
        for field, value, code in (
            ("provider_code", provider, "INVALID_PROVIDER"),
            ("transaction_reference", reference, "INVALID_REFERENCE"),
            ("amount", amount, "INVALID_DECIMAL"),
            ("currency", currency, "INVALID_CURRENCY"),
        ):
            if value is None:
                row_errors.append(_row_error(row_number, field, code, f"Invalid {field}."))
        for field in ("sender_phone", "receiver_phone"):
            if raw[field] and canonical[field] is None:
                row_errors.append(
                    _row_error(
                        row_number,
                        field,
                        "INVALID_GHANA_PHONE",
                        "Use a Ghanaian phone format.",
                    )
                )
        if raw["occurred_at"] and occurred_at is None:
            row_errors.append(
                _row_error(
                    row_number,
                    "occurred_at",
                    "INVALID_TIMESTAMP",
                    "Use an ISO or supported Ghana date/time format.",
                )
            )
        if raw["transaction_status"] and canonical["transaction_status"] is None:
            row_errors.append(
                _row_error(
                    row_number,
                    "transaction_status",
                    "INVALID_TRANSACTION_STATUS",
                    "Transaction status must contain 1 to 50 characters.",
                )
            )
        if len(raw["source_system_id"]) > 150:
            row_errors.append(
                _row_error(
                    row_number,
                    "source_system_id",
                    "SOURCE_SYSTEM_ID_TOO_LONG",
                    "Source-system identifiers must be 150 characters or fewer.",
                )
            )
        if date_warnings and occurred_at:
            canonical["normalisation_warnings"] = date_warnings
        duplicate_key = (provider or "", reference or "", canonical["source_system_id"] or "")
        if provider and reference and duplicate_key in seen:
            row_errors.append(
                _row_error(
                    row_number,
                    "transaction_reference",
                    "DUPLICATE_ROW",
                    "This provider/reference/source combination is repeated in the file.",
                )
            )
        seen.add(duplicate_key)
        if row_errors:
            errors.extend(row_errors)
        else:
            valid.append(ParsedReferenceRow(row_number, canonical, raw))
    if total == 0:
        raise VerificationFailure("REFERENCE_FILE_EMPTY", "The CSV contains no data rows.", 422)
    return ImportValidation(total, valid, errors)


def request_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def claim_idempotency(
    user: User, scope: str, key: str, request_hash: str
) -> tuple[IdempotencyRecord, bool]:
    if not 8 <= len(key) <= 200:
        raise VerificationFailure(
            "IDEMPOTENCY_KEY_INVALID", "Idempotency-Key must contain 8 to 200 characters.", 400
        )
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    lookup = select(IdempotencyRecord).where(
        IdempotencyRecord.principal_id == user.id,
        IdempotencyRecord.scope == scope,
        IdempotencyRecord.key_hash == key_hash,
    )
    record = db.session.scalar(lookup.with_for_update())
    if record is not None:
        return record, False
    candidate = IdempotencyRecord(
        principal_id=user.id,
        scope=scope,
        key_hash=key_hash,
        request_hash=request_hash,
        expires_at=datetime.now(UTC)
        + timedelta(hours=current_app.config["UPLOAD_IDEMPOTENCY_TTL_HOURS"]),
    )
    try:
        with db.session.begin_nested():
            db.session.add(candidate)
            db.session.flush()
        return candidate, True
    except IntegrityError:
        record = db.session.scalar(lookup.with_for_update())
        if record is None:
            raise
        return record, False


def upload_reference_import(
    *,
    user: User,
    roles: set[str],
    source_label: str,
    filename: str | None,
    content: bytes,
    idempotency_key: str,
    storage: ObjectStorage,
) -> ImportUploadResult:
    label = " ".join(source_label.split())
    if not 3 <= len(label) <= 200:
        raise VerificationFailure(
            "SOURCE_LABEL_INVALID", "Source label must contain 3 to 200 characters.", 422
        )
    display_filename = _clean_csv_filename(filename)
    _decode_csv(content)
    digest = sha256_bytes(content)
    request_digest = request_hash({"source_label": label, "file_sha256": digest})
    record, claimed = claim_idempotency(
        user, "POST:/api/v1/admin/reference-imports", idempotency_key, request_digest
    )
    if not claimed:
        if record.request_hash != request_digest:
            raise VerificationFailure(
                "IDEMPOTENCY_KEY_REUSED",
                "This Idempotency-Key was already used for a different import.",
                409,
            )
        existing = db.session.get(ReferenceImportBatch, record.resource_id)
        if existing is None:
            raise VerificationFailure(
                "IDEMPOTENCY_RESOURCE_UNAVAILABLE", "The original import is unavailable.", 409
            )
        return ImportUploadResult(existing, True)
    duplicate = db.session.scalar(
        select(ReferenceImportBatch).where(
            ReferenceImportBatch.source_label == label,
            ReferenceImportBatch.file_sha256 == digest,
        )
    )
    if duplicate is not None:
        record.resource_type = "reference_import_batch"
        record.resource_id = duplicate.id
        record.response_status = 200
        db.session.commit()
        return ImportUploadResult(duplicate, True)
    object_key = generated_key("reference-imports/originals", "csv")
    storage.put_bytes(
        object_key,
        content,
        "text/csv",
        {"sha256": digest, "classification": "private-reference-import"},
    )
    try:
        batch = ReferenceImportBatch(
            source_label=label,
            original_filename=display_filename,
            file_sha256=digest,
            object_key=object_key,
            status="UPLOADED",
            uploaded_by=user.id,
        )
        db.session.add(batch)
        db.session.flush()
        record.resource_type = "reference_import_batch"
        record.resource_id = batch.id
        record.response_status = 201
        audit_event(
            "reference_import.uploaded",
            "SUCCESS",
            actor_id=user.id,
            roles=roles,
            target_type="reference_import_batch",
            target_id=batch.id,
            metadata={"source_label": label, "file_sha256": digest, "size_bytes": len(content)},
        )
        db.session.commit()
        return ImportUploadResult(batch, False)
    except Exception:
        db.session.rollback()
        storage.delete(object_key)
        raise


def _safe_csv_cell(value: str) -> str:
    return f"'{value}" if value.startswith(("=", "+", "-", "@")) else value


def _invalid_report(validation: ImportValidation) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=("row", "field", "code", "message"))
    writer.writeheader()
    for error in validation.errors:
        writer.writerow({key: _safe_csv_cell(str(error[key])) for key in writer.fieldnames})
    return output.getvalue().encode("utf-8")


def validate_reference_import(
    *, batch: ReferenceImportBatch, user: User, roles: set[str], storage: ObjectStorage
) -> ImportValidation:
    if batch.status == "COMMITTED":
        raise VerificationFailure(
            "REFERENCE_IMPORT_ALREADY_COMMITTED", "Committed imports cannot be revalidated.", 409
        )
    if not batch.object_key:
        raise VerificationFailure(
            "REFERENCE_IMPORT_FILE_UNAVAILABLE", "The private import file is unavailable.", 503
        )
    try:
        content = storage.read_bytes(batch.object_key)
    except (OSError, ValueError) as exc:
        raise VerificationFailure(
            "REFERENCE_IMPORT_FILE_UNAVAILABLE", "The private import file is unavailable.", 503
        ) from exc
    if sha256_bytes(content) != batch.file_sha256:
        raise VerificationFailure(
            "REFERENCE_IMPORT_INTEGRITY_FAILED", "The import file failed its integrity check.", 409
        )
    validation = parse_reference_csv(content)
    report_key: str | None = None
    try:
        if validation.errors and not batch.invalid_report_key:
            report_key = generated_key("reference-imports/invalid-reports", "csv")
            storage.put_bytes(
                report_key,
                _invalid_report(validation),
                "text/csv",
                {"classification": "private-invalid-row-report"},
            )
            batch.invalid_report_key = report_key
        batch.status = "VALIDATED"
        batch.total_rows = validation.total_rows
        batch.valid_rows = len(validation.valid_rows)
        batch.invalid_rows = len({error["row"] for error in validation.errors})
        batch.validated_at = datetime.now(UTC)
        audit_event(
            "reference_import.validated",
            "SUCCESS",
            actor_id=user.id,
            roles=roles,
            target_type="reference_import_batch",
            target_id=batch.id,
            metadata={
                "total_rows": batch.total_rows,
                "valid_rows": batch.valid_rows,
                "invalid_rows": batch.invalid_rows,
            },
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        if report_key:
            storage.delete(report_key)
        raise
    return validation


def commit_reference_import(
    *,
    batch: ReferenceImportBatch,
    user: User,
    roles: set[str],
    idempotency_key: str,
    storage: ObjectStorage,
) -> tuple[int, bool]:
    request_digest = request_hash({"batch_id": str(batch.id), "action": "commit"})
    scope = f"POST:/api/v1/admin/reference-imports/{batch.id}/commit"
    record, claimed = claim_idempotency(user, scope, idempotency_key, request_digest)
    if not claimed:
        if record.resource_id != batch.id or record.request_hash != request_digest:
            raise VerificationFailure(
                "IDEMPOTENCY_KEY_REUSED",
                "This Idempotency-Key was already used for a different commit.",
                409,
            )
        if batch.status != "COMMITTED":
            raise VerificationFailure(
                "IDEMPOTENCY_RESOURCE_UNAVAILABLE", "The original commit is unavailable.", 409
            )
        return batch.valid_rows, True
    if batch.status != "VALIDATED":
        raise VerificationFailure(
            "REFERENCE_IMPORT_NOT_VALIDATED", "Validate the import before committing it.", 409
        )
    if not batch.object_key:
        raise VerificationFailure(
            "REFERENCE_IMPORT_FILE_UNAVAILABLE", "The private import file is unavailable.", 503
        )
    try:
        content = storage.read_bytes(batch.object_key)
    except (OSError, ValueError) as exc:
        raise VerificationFailure(
            "REFERENCE_IMPORT_FILE_UNAVAILABLE", "The private import file is unavailable.", 503
        ) from exc
    if sha256_bytes(content) != batch.file_sha256:
        raise VerificationFailure(
            "REFERENCE_IMPORT_INTEGRITY_FAILED", "The import file failed its integrity check.", 409
        )
    validation = parse_reference_csv(content)
    if not validation.valid_rows:
        raise VerificationFailure(
            "REFERENCE_IMPORT_HAS_NO_VALID_ROWS",
            "The import has no valid rows to commit.",
            409,
        )
    if len(validation.valid_rows) != batch.valid_rows:
        raise VerificationFailure(
            "REFERENCE_IMPORT_PREVIEW_CHANGED",
            "The import no longer matches its validated preview.",
            409,
        )
    for item in validation.valid_rows:
        row = item.canonical
        occurred_at = (
            datetime.fromisoformat(row["occurred_at"].replace("Z", "+00:00"))
            if row["occurred_at"]
            else None
        )
        db.session.add(
            ReferenceTransaction(
                import_batch_id=batch.id,
                provider_code=row["provider_code"],
                transaction_reference=row["transaction_reference"],
                amount=Decimal(row["amount"]),
                currency=row["currency"],
                sender_name_normalised=row["sender_name"],
                sender_phone_e164=row["sender_phone"],
                receiver_name_normalised=row["receiver_name"],
                receiver_phone_e164=row["receiver_phone"],
                occurred_at=occurred_at,
                transaction_status=row["transaction_status"],
                source_system_id=row["source_system_id"],
                raw_row=item.raw,
            )
        )
    batch.status = "COMMITTED"
    batch.committed_at = datetime.now(UTC)
    record.resource_type = "reference_import_batch"
    record.resource_id = batch.id
    record.response_status = 200
    audit_event(
        "reference_import.committed",
        "SUCCESS",
        actor_id=user.id,
        roles=roles,
        target_type="reference_import_batch",
        target_id=batch.id,
        metadata={"committed_rows": len(validation.valid_rows)},
    )
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise VerificationFailure(
            "REFERENCE_IMPORT_DUPLICATE_CONFLICT",
            "A committed reference already uses one of the source identifiers.",
            409,
        ) from exc
    return len(validation.valid_rows), False


def _masked(value: str | None) -> str | None:
    if not value:
        return None
    return value if len(value) <= 7 else f"{value[:4]}...{value[-2:]}"


def batch_projection(batch: ReferenceImportBatch) -> dict[str, Any]:
    return {
        "id": batch.id,
        "source_label": batch.source_label,
        "original_filename": batch.original_filename,
        "file_sha256": batch.file_sha256,
        "status": batch.status,
        "total_rows": batch.total_rows,
        "valid_rows": batch.valid_rows,
        "invalid_rows": batch.invalid_rows,
        "uploaded_by": batch.uploaded_by,
        "validated_at": batch.validated_at,
        "committed_at": batch.committed_at,
        "created_at": batch.created_at,
        "invalid_rows_download": (
            f"/api/v1/admin/reference-imports/{batch.id}/invalid-rows"
            if batch.invalid_report_key
            else None
        ),
    }


def reference_projection(reference: ReferenceTransaction) -> dict[str, Any]:
    return {
        "id": reference.id,
        "provider_code": reference.provider_code,
        "transaction_reference_masked": _masked(reference.transaction_reference),
        "amount": f"{reference.amount:.2f}",
        "currency": reference.currency,
        "sender_phone_masked": _masked(reference.sender_phone_e164),
        "receiver_phone_masked": _masked(reference.receiver_phone_e164),
        "occurred_at": reference.occurred_at,
        "transaction_status": reference.transaction_status,
        "source_label": reference.import_batch.source_label,
        "import_batch_id": reference.import_batch_id,
        "created_at": reference.created_at,
    }


def _comparison(
    observed: Any,
    expected: Any,
    *,
    matched: bool | None,
    tolerance: dict[str, Any] | None = None,
    score: float | None = None,
) -> dict[str, Any]:
    status = "NOT_AVAILABLE" if matched is None else "MATCH" if matched else "MISMATCH"
    comparison_tolerance = tolerance or {"type": "EXACT"}
    return {
        "status": status,
        "observed": _masked(str(observed)) if observed is not None else None,
        "expected": _masked(str(expected)) if expected is not None else None,
        "tolerance": comparison_tolerance,
        "mode": comparison_tolerance["type"],
        "score": score
        if score is not None
        else (1.0 if matched else 0.0 if matched is False else None),
        "reason": {
            "MATCH": "FIELD_MATCHED",
            "MISMATCH": "FIELD_DIFFERED",
            "NOT_AVAILABLE": "COMPARISON_DATA_UNAVAILABLE",
        }[status],
    }


def evaluate_verification(confirmed_fields: dict[str, Any]) -> VerificationOutcome:
    provider = _canonical_provider(str(confirmed_fields.get("provider_code", "")))
    reference = normalize_reference(str(confirmed_fields.get("transaction_reference", "")))
    verifier_version = current_app.config["VERIFIER_VERSION"]
    if not reference:
        return VerificationOutcome(
            "UNVERIFIED",
            None,
            "NO_CANONICAL_REFERENCE",
            {},
            0,
            0,
            ["CANONICAL_REFERENCE_UNAVAILABLE"],
            verifier_version,
        )
    candidates: list[ReferenceTransaction] = []
    method = "PROVIDER_REFERENCE_EXACT"
    if provider and provider != "GENERIC_MOMO":
        candidates = list(
            db.session.scalars(
                select(ReferenceTransaction)
                .join(ReferenceImportBatch)
                .where(
                    ReferenceImportBatch.status == "COMMITTED",
                    ReferenceTransaction.provider_code == provider,
                    ReferenceTransaction.transaction_reference == reference,
                )
                .order_by(ReferenceTransaction.created_at.desc())
            )
        )
    if not candidates and (not provider or provider == "GENERIC_MOMO"):
        fallback = list(
            db.session.scalars(
                select(ReferenceTransaction)
                .join(ReferenceImportBatch)
                .where(
                    ReferenceImportBatch.status == "COMMITTED",
                    ReferenceTransaction.transaction_reference == reference,
                )
                .order_by(ReferenceTransaction.created_at.desc())
                .limit(2)
            )
        )
        if fallback:
            candidates = fallback
            method = (
                "UNIQUE_REFERENCE_FALLBACK"
                if len(fallback) == 1
                else "AMBIGUOUS_REFERENCE_FALLBACK"
            )
    if not candidates:
        return VerificationOutcome(
            "UNVERIFIED",
            None,
            "NO_REFERENCE_RECORD",
            {},
            0,
            0,
            ["NO_STORED_REFERENCE_RECORD"],
            verifier_version,
        )
    if len(candidates) > 1:
        return VerificationOutcome(
            "UNVERIFIED",
            None,
            "AMBIGUOUS_PROVIDER_REFERENCE",
            {},
            0,
            0,
            ["MULTIPLE_REFERENCE_CANDIDATES"],
            verifier_version,
        )
    selected = candidates[0]
    warnings = ["PROVIDER_FALLBACK_USED"] if method == "UNIQUE_REFERENCE_FALLBACK" else []
    comparisons: dict[str, dict[str, Any]] = {}
    observed_amount = normalize_amount(str(confirmed_fields.get("amount", "")))
    amount_tolerance = Decimal(str(current_app.config["REFERENCE_AMOUNT_TOLERANCE"]))
    amount_match = (
        observed_amount is not None
        and abs(Decimal(observed_amount) - selected.amount) <= amount_tolerance
    )
    comparisons["amount"] = _comparison(
        observed_amount,
        f"{selected.amount:.2f}",
        matched=amount_match,
        tolerance={"type": "ABSOLUTE", "value": f"{amount_tolerance:.2f}", "unit": "GHS"},
    )
    observed_currency = _canonical_currency(str(confirmed_fields.get("currency", "")))
    comparisons["currency"] = _comparison(
        observed_currency, selected.currency, matched=observed_currency == selected.currency
    )
    for field, reference_value in (
        ("sender_phone", selected.sender_phone_e164),
        ("receiver_phone", selected.receiver_phone_e164),
    ):
        observed = normalize_phone(str(confirmed_fields.get(field, "")))
        comparisons[field] = _comparison(
            observed,
            reference_value,
            matched=None if not observed or not reference_value else observed == reference_value,
        )
    name_threshold = current_app.config["REFERENCE_NAME_SIMILARITY_THRESHOLD"]
    for field, reference_value in (
        ("sender_name", selected.sender_name_normalised),
        ("receiver_name", selected.receiver_name_normalised),
    ):
        observed = normalize_name(str(confirmed_fields.get(field, "")))
        similarity = (
            SequenceMatcher(None, observed, reference_value).ratio()
            if observed and reference_value
            else None
        )
        comparisons[field] = _comparison(
            observed,
            reference_value,
            matched=None if similarity is None else similarity >= name_threshold,
            tolerance={"type": "SIMILARITY", "minimum": name_threshold, "observed": similarity},
            score=similarity,
        )
    observed_time_raw, _ = normalize_occurred_at(str(confirmed_fields.get("occurred_at", "")))
    observed_time = (
        datetime.fromisoformat(observed_time_raw.replace("Z", "+00:00"))
        if observed_time_raw
        else None
    )
    seconds = current_app.config["REFERENCE_TIMESTAMP_TOLERANCE_MINUTES"] * 60
    time_match = (
        None
        if observed_time is None or selected.occurred_at is None
        else abs((observed_time - selected.occurred_at).total_seconds()) <= seconds
    )
    comparisons["occurred_at"] = _comparison(
        observed_time_raw,
        selected.occurred_at.isoformat() if selected.occurred_at else None,
        matched=time_match,
        tolerance={"type": "ABSOLUTE", "value": seconds, "unit": "seconds"},
    )
    observed_status = _canonical_status(str(confirmed_fields.get("status_text", "")))
    comparisons["transaction_status"] = _comparison(
        observed_status,
        selected.transaction_status,
        matched=(
            None
            if not observed_status or not selected.transaction_status
            else observed_status == selected.transaction_status
        ),
    )
    matched_count = sum(item["status"] == "MATCH" for item in comparisons.values())
    mismatched_count = sum(item["status"] == "MISMATCH" for item in comparisons.values())
    critical_mismatch = any(comparisons[field]["status"] == "MISMATCH" for field in CRITICAL_FIELDS)
    critical_unavailable = any(
        comparisons[field]["status"] == "NOT_AVAILABLE" for field in CRITICAL_FIELDS
    )
    if critical_unavailable:
        warnings.append("INSUFFICIENT_REFERENCE_COMPARISON_DATA")
    return VerificationOutcome(
        "MISMATCH" if critical_mismatch else "UNVERIFIED" if critical_unavailable else "VERIFIED",
        selected,
        method,
        comparisons,
        matched_count,
        mismatched_count,
        warnings,
        verifier_version,
    )


def verification_reuse_warnings(
    transaction: Transaction, reference: ReferenceTransaction | None
) -> list[str]:
    warnings: list[str] = []
    if reference is not None:
        uses = (
            db.session.scalar(
                select(func.count(VerificationResult.id)).where(
                    VerificationResult.reference_transaction_id == reference.id
                )
            )
            or 0
        )
        if uses > 0:
            warnings.append("REFERENCE_PREVIOUSLY_USED")
    if transaction.receipt is not None:
        receipt_count = (
            db.session.scalar(
                select(func.count(Receipt.id)).where(
                    Receipt.sha256 == transaction.receipt.sha256,
                    Receipt.transaction_id != transaction.id,
                )
            )
            or 0
        )
        if receipt_count > 0:
            warnings.append("RECEIPT_REUSED")
    return warnings


def run_partial_verification_analysis(
    *,
    transaction: Transaction,
    confirmation: OCRConfirmation,
    user: User,
    roles: set[str],
    idempotency_key: str,
    storage: ObjectStorage,
) -> PartialAnalysisResult:
    rule_set = db.session.scalar(
        select(FraudRuleSet)
        .where(FraudRuleSet.status == "ACTIVE")
        .order_by(FraudRuleSet.activated_at.desc().nullslast(), FraudRuleSet.created_at.desc())
    )
    if rule_set is None:
        raise VerificationFailure(
            "ANALYSIS_CONFIGURATION_UNAVAILABLE",
            "Stored-record verification is configured, but no active rule set is available.",
            503,
        )
    request_digest = request_hash(
        {"transaction_id": str(transaction.id), "confirmation_id": str(confirmation.id)}
    )
    scope = f"POST:/api/v1/transactions/{transaction.id}/analyses"
    record, claimed = claim_idempotency(user, scope, idempotency_key, request_digest)
    if not claimed:
        if record.request_hash != request_digest:
            raise VerificationFailure(
                "IDEMPOTENCY_KEY_REUSED",
                "This Idempotency-Key was already used for a different analysis request.",
                409,
            )
        run = db.session.get(AnalysisRun, record.resource_id)
        verification = (
            db.session.scalar(
                select(VerificationResult).where(VerificationResult.analysis_run_id == run.id)
            )
            if run is not None
            else None
        )
        replay_image_analysis = (
            db.session.scalar(select(ImageAnalysis).where(ImageAnalysis.analysis_run_id == run.id))
            if run is not None
            else None
        )
        image_stage = (
            db.session.scalar(
                select(AnalysisStageRun).where(
                    AnalysisStageRun.analysis_run_id == run.id,
                    AnalysisStageRun.stage == "IMAGE_ANALYSIS",
                    AnalysisStageRun.attempt == 1,
                )
            )
            if run is not None
            else None
        )
        if run is None or verification is None or run.transaction_id != transaction.id:
            raise VerificationFailure(
                "IDEMPOTENCY_RESOURCE_UNAVAILABLE", "The original analysis is unavailable.", 409
            )
        return PartialAnalysisResult(
            run,
            verification,
            replay_image_analysis,
            image_stage.error_code if image_stage is not None else "IMAGE_ANALYSIS_UNAVAILABLE",
            True,
        )
    now = datetime.now(UTC)
    outcome = evaluate_verification(confirmation.confirmed_fields)
    warnings = list(
        dict.fromkeys(
            outcome.warnings + verification_reuse_warnings(transaction, outcome.reference)
        )
    )
    run = AnalysisRun(
        transaction_id=transaction.id,
        ocr_confirmation_id=confirmation.id,
        status="PARTIAL",
        current_stage="DETERMINISTIC_EVIDENCE_PROCESSING",
        rule_set_id=rule_set.id,
        idempotency_key_hash=record.key_hash,
        request_fingerprint=request_digest,
        attempt_count=1,
        queued_at=now,
        started_at=now,
        completed_at=now,
        component_scores={
            "verification_status": outcome.status,
            "image_evidence_status": "PROCESSING",
        },
        top_reasons=[],
        configuration_snapshot={
            "verifier_version": outcome.verifier_version,
            "rule_set_version": rule_set.version,
            "reference_amount_tolerance": current_app.config["REFERENCE_AMOUNT_TOLERANCE"],
            "reference_timestamp_tolerance_minutes": current_app.config[
                "REFERENCE_TIMESTAMP_TOLERANCE_MINUTES"
            ],
            "reference_name_similarity_threshold": current_app.config[
                "REFERENCE_NAME_SIMILARITY_THRESHOLD"
            ],
            "image_forensics_version": current_app.config["IMAGE_FORENSICS_VERSION"],
            "image_feature_schema_version": "deterministic-image-features-v1",
            "image_evidence_thresholds": {
                "ela_regional_cv": current_app.config["IMAGE_FORENSICS_ELA_REGIONAL_CV_THRESHOLD"],
                "noise_regional_cv": current_app.config[
                    "IMAGE_FORENSICS_NOISE_REGIONAL_CV_THRESHOLD"
                ],
                "baseline_deviation": current_app.config["IMAGE_FORENSICS_BASELINE_THRESHOLD"],
                "box_height_cv": current_app.config["IMAGE_FORENSICS_HEIGHT_CV_THRESHOLD"],
                "edge_margin": current_app.config["IMAGE_FORENSICS_EDGE_MARGIN_THRESHOLD"],
            },
        },
        error_code="ANALYSIS_COMPONENTS_UNAVAILABLE",
        error_message_safe=(
            "Stored/imported reference verification completed. Model and risk stages are not "
            "available yet."
        ),
    )
    db.session.add(run)
    db.session.flush()
    verification = VerificationResult(
        analysis_run_id=run.id,
        reference_transaction_id=outcome.reference.id if outcome.reference else None,
        status=outcome.status,
        verifier_version=outcome.verifier_version,
        candidate_method=outcome.candidate_method,
        field_comparisons=outcome.comparisons,
        matched_field_count=outcome.matched_count,
        mismatched_field_count=outcome.mismatched_count,
        warnings=warnings,
    )
    db.session.add(verification)
    image_analysis: ImageAnalysis | None = None
    image_error_code: str | None = None
    written_keys: tuple[str, ...] = ()
    try:
        with db.session.begin_nested():
            image_outcome = run_image_forensics(
                run=run,
                transaction=transaction,
                ocr_result=confirmation.ocr_result,
                storage=storage,
            )
            image_analysis = image_outcome.image_analysis
            written_keys = image_outcome.written_keys
    except ImageForensicsFailure as failure:
        image_error_code = failure.code
        current_app.logger.warning(
            "image_forensics_unavailable",
            extra={"transaction_id": str(transaction.id), "reason_code": failure.code},
        )
    run.current_stage = (
        "DETERMINISTIC_EVIDENCE_COMPLETE" if image_analysis is not None else "VERIFICATION_COMPLETE"
    )
    run.component_scores = {
        "verification_status": outcome.status,
        "image_evidence_status": "COMPLETED" if image_analysis is not None else "UNAVAILABLE",
    }
    run.error_message_safe = (
        "Stored/imported verification and deterministic supporting image evidence completed. "
        "Model and risk stages are not available yet."
        if image_analysis is not None
        else "Stored/imported verification completed. Deterministic image evidence was "
        "unavailable; model and risk stages are also unavailable."
    )
    stages = (
        ("REFERENCE_VERIFICATION", "COMPLETED", None),
        (
            "IMAGE_ANALYSIS",
            "COMPLETED" if image_analysis is not None else "FAILED",
            image_error_code,
        ),
        ("STRUCTURED_MODEL", "SKIPPED", "MODEL_NOT_TRAINED"),
        ("IMAGE_MODEL", "SKIPPED", "MODEL_NOT_TRAINED"),
        ("RISK_AGGREGATION", "SKIPPED", "P13_NOT_IMPLEMENTED"),
    )
    for stage, status, error_code in stages:
        db.session.add(
            AnalysisStageRun(
                analysis_run_id=run.id,
                stage=stage,
                status=status,
                attempt=1,
                started_at=now,
                completed_at=now,
                duration_ms=0,
                error_code=error_code,
                details={"verification_status": outcome.status}
                if stage == "REFERENCE_VERIFICATION"
                else {
                    "algorithm_version": current_app.config["IMAGE_FORENSICS_VERSION"],
                    "supporting_evidence_only": True,
                    "final_classification_emitted": False,
                }
                if stage == "IMAGE_ANALYSIS"
                else {},
            )
        )
    transaction.status = "PARTIAL"
    transaction.latest_analysis_run_id = run.id
    record.resource_type = "analysis_run"
    record.resource_id = run.id
    record.response_status = 202
    audit_event(
        "verification.completed",
        "SUCCESS",
        actor_id=user.id,
        roles=roles,
        target_type="analysis_run",
        target_id=run.id,
        metadata={
            "transaction_id": str(transaction.id),
            "verification_status": outcome.status,
            "candidate_method": outcome.candidate_method,
            "verifier_version": outcome.verifier_version,
            "warning_codes": warnings,
            "image_evidence_status": "COMPLETED" if image_analysis is not None else "UNAVAILABLE",
            "image_forensics_version": current_app.config["IMAGE_FORENSICS_VERSION"],
        },
    )
    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        for key in reversed(written_keys):
            try:
                storage.delete(key)
            except Exception:
                current_app.logger.exception("image_forensics_commit_cleanup_failed")
        current_app.logger.exception("analysis_persistence_failed", exc_info=exc)
        raise VerificationFailure(
            "ANALYSIS_PERSISTENCE_UNAVAILABLE",
            "The analysis evidence could not be stored safely. Retry with the same key.",
            503,
        ) from exc
    return PartialAnalysisResult(run, verification, image_analysis, image_error_code, False)


def verification_projection(result: VerificationResult) -> dict[str, Any]:
    summaries = {
        "VERIFIED": (
            "A stored/imported reference record was found and the available critical fields "
            "matched."
        ),
        "MISMATCH": (
            "A stored/imported reference record was found, but one or more critical fields "
            "differed."
        ),
        "UNVERIFIED": "No usable stored/imported reference record was available.",
        "NOT_ATTEMPTED": (
            "Stored-record verification was not requested for this screenshot-only analysis."
        ),
    }
    run = db.session.get(AnalysisRun, result.analysis_run_id)
    rule_set = db.session.get(FraudRuleSet, run.rule_set_id) if run else None
    return {
        "status": result.status,
        "label": "Not attempted" if result.status == "NOT_ATTEMPTED" else result.status.title(),
        "basis": (
            "NOT_APPLICABLE_SCREENSHOT_ONLY"
            if result.status == "NOT_ATTEMPTED"
            else "STORED_IMPORTED_RECORD"
        ),
        "summary": summaries[result.status],
        "reference_transaction_id": result.reference_transaction_id,
        "candidate_method": result.candidate_method,
        "verifier_version": result.verifier_version,
        "rule_set_version": rule_set.version if rule_set else None,
        "field_comparisons": result.field_comparisons,
        "matched_field_count": result.matched_field_count,
        "mismatched_field_count": result.mismatched_field_count,
        "warnings": result.warnings,
        "disclaimer": (
            "No transaction verification was attempted in screenshot-only mode."
            if result.status == "NOT_ATTEMPTED"
            else "This is not live confirmation from a mobile-network operator."
        ),
    }


__all__ = [
    "CSV_COLUMNS",
    "ImportValidation",
    "VerificationFailure",
    "VerificationOutcome",
    "batch_projection",
    "claim_idempotency",
    "commit_reference_import",
    "evaluate_verification",
    "parse_reference_csv",
    "reference_projection",
    "request_hash",
    "run_partial_verification_analysis",
    "upload_reference_import",
    "validate_reference_import",
    "verification_projection",
    "verification_reuse_warnings",
]
