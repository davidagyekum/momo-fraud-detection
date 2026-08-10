"""Typed manifest loading, governance validation and canonical dataset hashing."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Final

from PIL import Image, UnidentifiedImageError

MANIFEST_SCHEMA_VERSION: Final = "receipt-dataset-manifest-v1"
ALLOWED_SOURCE_TYPES: Final = {"real_authorised", "synthetic", "controlled_tamper"}
ALLOWED_LABELS: Final = {"genuine", "suspicious", "fraudulent"}
ALLOWED_SPLITS: Final = {"train", "validation", "test"}
ALLOWED_ANONYMISATION: Final = {"anonymised", "not_applicable"}
IMAGE_SUFFIXES: Final = {".jpg", ".jpeg", ".png", ".webp"}
SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
PHONE_PATTERN: Final = re.compile(r"(?<!\d)(?:\+?233|0)[235]\d{8}(?!\d)")
EMAIL_PATTERN: Final = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
REFERENCE_PATTERN: Final = re.compile(
    r"(?i)\b(?:reference|transaction[_ ]?id)\s*[:=]\s*"
    r"(?!DEMO-|SYNTH-|REDACTED)[A-Z0-9-]{8,}"
)
NAME_PATTERN: Final = re.compile(
    r"(?i)\b(?:customer|recipient|sender|name)\s*[:=]\s*"
    r"(?!DEMO\b|SYNTHETIC\b|REDACTED\b|ANONYMOUS\b)"
    r"[A-Z][A-Z'-]+(?:\s+[A-Z][A-Z'-]+)+"
)

MANIFEST_COLUMNS: Final = (
    "sample_id",
    "relative_path",
    "private_object_id",
    "sha256",
    "source_group_id",
    "parent_sample_id",
    "source_type",
    "provider_code",
    "label",
    "tamper_operations",
    "tamper_metadata",
    "split",
    "consent_or_licence_reference",
    "contains_personal_data",
    "anonymisation_status",
    "generated_seed",
    "notes",
)
REQUIRED_COLUMNS: Final = set(MANIFEST_COLUMNS) - {
    "private_object_id",
    "tamper_metadata",
}


class ManifestError(ValueError):
    """Raised when a manifest cannot be parsed safely."""


@dataclass(frozen=True)
class ManifestRecord:
    """One governed receipt image or private object in a dataset manifest."""

    sample_id: str
    relative_path: str
    private_object_id: str
    sha256: str
    source_group_id: str
    parent_sample_id: str
    source_type: str
    provider_code: str
    label: str
    tamper_operations: tuple[str, ...]
    tamper_metadata: str
    split: str
    consent_or_licence_reference: str
    contains_personal_data: bool
    anonymisation_status: str
    generated_seed: int | None
    notes: str

    def canonical_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible representation."""

        value = asdict(self)
        value["tamper_operations"] = list(self.tamper_operations)
        return value

    def csv_dict(self) -> dict[str, str]:
        """Return the canonical CSV representation."""

        return {
            "sample_id": self.sample_id,
            "relative_path": self.relative_path,
            "private_object_id": self.private_object_id,
            "sha256": self.sha256,
            "source_group_id": self.source_group_id,
            "parent_sample_id": self.parent_sample_id,
            "source_type": self.source_type,
            "provider_code": self.provider_code,
            "label": self.label,
            "tamper_operations": ";".join(self.tamper_operations),
            "tamper_metadata": self.tamper_metadata,
            "split": self.split,
            "consent_or_licence_reference": self.consent_or_licence_reference,
            "contains_personal_data": str(self.contains_personal_data).lower(),
            "anonymisation_status": self.anonymisation_status,
            "generated_seed": ("" if self.generated_seed is None else str(self.generated_seed)),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class DatasetManifest:
    """A parsed manifest with canonical content and split hashes."""

    path: Path
    records: tuple[ManifestRecord, ...]

    @property
    def manifest_hash(self) -> str:
        payload = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "records": [record.canonical_dict() for record in self.records],
        }
        return _canonical_hash(payload)

    @property
    def split_hash(self) -> str:
        mapping = sorted({(record.source_group_id, record.split) for record in self.records})
        return _canonical_hash(
            {
                "schema_version": MANIFEST_SCHEMA_VERSION,
                "source_group_splits": mapping,
            }
        )


@dataclass(frozen=True)
class ValidationIssue:
    """A machine-readable dataset validation finding."""

    severity: str
    code: str
    message: str
    sample_id: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    """Validation result with reproducibility hashes and distributions."""

    schema_version: str
    manifest_hash: str
    split_hash: str
    record_count: int
    group_count: int
    split_counts: Mapping[str, int]
    label_counts: Mapping[str, int]
    source_type_counts: Mapping[str, int]
    issues: tuple[ValidationIssue, ...]

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def raise_for_errors(self) -> None:
        if self.errors:
            codes = ", ".join(sorted({issue.code for issue in self.errors}))
            raise ManifestError(f"dataset validation failed: {codes}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "manifest_hash": self.manifest_hash,
            "split_hash": self.split_hash,
            "record_count": self.record_count,
            "group_count": self.group_count,
            "split_counts": dict(sorted(self.split_counts.items())),
            "label_counts": dict(sorted(self.label_counts.items())),
            "source_type_counts": dict(sorted(self.source_type_counts.items())),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [asdict(issue) for issue in self.issues],
        }


def _canonical_hash(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def _parse_boolean(value: str, *, line_number: int) -> bool:
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise ManifestError(f"line {line_number}: contains_personal_data must be true or false")


def _parse_seed(value: str, *, line_number: int) -> int | None:
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return int(stripped)
    except ValueError as exc:
        raise ManifestError(f"line {line_number}: generated_seed must be an integer") from exc


def _normalise_row(row: Mapping[str, str | None], *, line_number: int) -> ManifestRecord:
    values = {key: (value or "").strip() for key, value in row.items() if key is not None}
    return ManifestRecord(
        sample_id=values.get("sample_id", ""),
        relative_path=values.get("relative_path", "").replace("\\", "/"),
        private_object_id=values.get("private_object_id", ""),
        sha256=values.get("sha256", "").lower(),
        source_group_id=values.get("source_group_id", ""),
        parent_sample_id=values.get("parent_sample_id", ""),
        source_type=values.get("source_type", "").lower(),
        provider_code=values.get("provider_code", ""),
        label=values.get("label", "").lower(),
        tamper_operations=tuple(
            operation.strip()
            for operation in values.get("tamper_operations", "").split(";")
            if operation.strip()
        ),
        tamper_metadata=values.get("tamper_metadata", ""),
        split=values.get("split", "").lower(),
        consent_or_licence_reference=values.get("consent_or_licence_reference", ""),
        contains_personal_data=_parse_boolean(
            values.get("contains_personal_data", ""), line_number=line_number
        ),
        anonymisation_status=values.get("anonymisation_status", "").lower(),
        generated_seed=_parse_seed(values.get("generated_seed", ""), line_number=line_number),
        notes=values.get("notes", ""),
    )


def load_manifest(path: Path) -> DatasetManifest:
    """Load a UTF-8 CSV manifest and reject malformed schemas or duplicate IDs."""

    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ManifestError("manifest has no header")
            fields = {field.strip() for field in reader.fieldnames}
            missing = sorted(REQUIRED_COLUMNS - fields)
            if missing:
                raise ManifestError(f"manifest is missing columns: {', '.join(missing)}")
            records = tuple(
                _normalise_row(row, line_number=line_number)
                for line_number, row in enumerate(reader, start=2)
            )
    except UnicodeDecodeError as exc:
        raise ManifestError("manifest must be valid UTF-8") from exc
    except OSError as exc:
        raise ManifestError(f"unable to read manifest: {exc}") from exc
    if not records:
        raise ManifestError("manifest must contain at least one record")
    return DatasetManifest(path=path, records=records)


def write_manifest(path: Path, records: Iterable[ManifestRecord]) -> DatasetManifest:
    """Write a canonical UTF-8 CSV manifest and load it back."""

    ordered = tuple(sorted(records, key=lambda record: record.sample_id))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(record.csv_dict() for record in ordered)
    return load_manifest(path)


def sha256_file(path: Path) -> str:
    """Hash a file without loading it all into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_text_for_private_identifiers(text: str) -> tuple[str, ...]:
    """Return conservative private-identifier categories found in research text."""

    categories: list[str] = []
    if PHONE_PATTERN.search(text):
        categories.append("phone_number")
    if EMAIL_PATTERN.search(text):
        categories.append("email_address")
    if REFERENCE_PATTERN.search(text):
        categories.append("transaction_reference")
    if NAME_PATTERN.search(text.upper()):
        categories.append("personal_name")
    return tuple(categories)


def _safe_local_path(root: Path, relative_path: str) -> Path | None:
    pure = PurePosixPath(relative_path)
    if not relative_path or pure.is_absolute() or ".." in pure.parts:
        return None
    candidate = (root / Path(*pure.parts)).resolve()
    resolved_root = root.resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        return None
    return candidate


def _issue(
    issues: list[ValidationIssue],
    code: str,
    message: str,
    record: ManifestRecord | None = None,
    *,
    severity: str = "error",
) -> None:
    issues.append(
        ValidationIssue(
            severity=severity,
            code=code,
            message=message,
            sample_id=None if record is None else record.sample_id,
        )
    )


def _validate_record_fields(
    record: ManifestRecord, root: Path, issues: list[ValidationIssue]
) -> None:
    if not record.sample_id or not record.source_group_id:
        _issue(issues, "missing_identity", "sample_id and source_group_id are required", record)
    if record.source_type not in ALLOWED_SOURCE_TYPES:
        _issue(issues, "invalid_source_type", "source_type is not allowed", record)
    if record.label not in ALLOWED_LABELS:
        _issue(issues, "invalid_label", "label is not allowed", record)
    if record.split not in ALLOWED_SPLITS:
        _issue(issues, "invalid_split", "split is not allowed", record)
    if record.anonymisation_status not in ALLOWED_ANONYMISATION:
        _issue(issues, "invalid_anonymisation", "anonymisation_status is not allowed", record)
    if not record.consent_or_licence_reference:
        _issue(issues, "missing_permission", "consent or licence reference is required", record)
    if bool(record.relative_path) == bool(record.private_object_id):
        _issue(
            issues,
            "invalid_location",
            "exactly one of relative_path or private_object_id is required",
            record,
        )
    if not SHA256_PATTERN.fullmatch(record.sha256):
        _issue(
            issues, "invalid_sha256", "sha256 must be 64 lowercase hexadecimal characters", record
        )
    if record.source_type in {"synthetic", "controlled_tamper"}:
        if record.contains_personal_data:
            _issue(
                issues,
                "synthetic_personal_data",
                "controlled/synthetic samples must not contain personal data",
                record,
            )
        if record.anonymisation_status != "not_applicable":
            _issue(
                issues,
                "synthetic_anonymisation_status",
                "controlled/synthetic samples must use not_applicable anonymisation",
                record,
            )
        if record.generated_seed is None:
            _issue(issues, "missing_generation_seed", "generated_seed is required", record)
    if record.source_type == "real_authorised":
        if record.contains_personal_data and record.anonymisation_status != "anonymised":
            _issue(
                issues,
                "real_data_not_anonymised",
                "authorised real personal data must be anonymised before research use",
                record,
            )
        if record.relative_path:
            _issue(
                issues,
                "real_data_in_repository_path",
                "authorised real data must use a private object ID, not a repository path",
                record,
            )
    if record.source_type == "controlled_tamper":
        if not record.parent_sample_id or not record.tamper_operations:
            _issue(
                issues,
                "incomplete_tamper_provenance",
                "controlled tamper requires a parent and operations",
                record,
            )
        try:
            metadata = json.loads(record.tamper_metadata)
        except json.JSONDecodeError:
            _issue(issues, "invalid_tamper_metadata", "tamper_metadata must be valid JSON", record)
        else:
            described = (
                {
                    item.get("name")
                    for item in metadata.get("operations", [])
                    if isinstance(item, dict)
                }
                if isinstance(metadata, dict)
                else set()
            )
            if set(record.tamper_operations) != described:
                _issue(
                    issues,
                    "tamper_metadata_mismatch",
                    "tamper metadata must describe every operation exactly once",
                    record,
                )
    elif record.parent_sample_id or record.tamper_operations or record.tamper_metadata:
        _issue(
            issues,
            "unexpected_tamper_provenance",
            "non-tamper samples cannot carry parent or tamper operations",
            record,
        )
    for operation in record.tamper_operations:
        if operation.startswith("augment:") and record.split != "train":
            _issue(
                issues,
                "augmentation_outside_train",
                "augmentation is allowed only after splitting and only for training",
                record,
            )
    private_categories = scan_text_for_private_identifiers(
        f"{record.notes}\n{record.tamper_metadata}"
    )
    if private_categories and not record.contains_personal_data:
        _issue(
            issues,
            "unapproved_private_identifier",
            f"unapproved identifier pattern(s): {', '.join(private_categories)}",
            record,
        )

    if not record.relative_path:
        return
    local_path = _safe_local_path(root, record.relative_path)
    if local_path is None:
        _issue(
            issues, "unsafe_path", "relative_path is absolute or escapes the dataset root", record
        )
        return
    if local_path.suffix.lower() not in IMAGE_SUFFIXES:
        _issue(issues, "unsupported_image_type", "receipt image type is not supported", record)
    if not local_path.is_file():
        _issue(issues, "missing_file", "manifest image does not exist", record)
        return
    try:
        actual_hash = sha256_file(local_path)
    except OSError as exc:
        _issue(issues, "unreadable_file", f"unable to hash image: {exc}", record)
        return
    if actual_hash != record.sha256:
        _issue(issues, "hash_mismatch", "recorded SHA-256 does not match image bytes", record)
    try:
        with Image.open(local_path) as image:
            image.verify()
        with Image.open(local_path) as image:
            width, height = image.size
            if width < 128 or height < 128:
                _issue(
                    issues,
                    "image_too_small",
                    "research image must be at least 128 by 128 pixels",
                    record,
                )
    except (OSError, UnidentifiedImageError) as exc:
        _issue(issues, "corrupt_image", f"image cannot be decoded: {exc}", record)


def validate_manifest(manifest: DatasetManifest, *, root: Path) -> ValidationReport:
    """Validate files, provenance, privacy and source-group split isolation."""

    issues: list[ValidationIssue] = []
    by_id: dict[str, ManifestRecord] = {}
    by_hash: dict[str, list[ManifestRecord]] = defaultdict(list)
    group_splits: dict[str, set[str]] = defaultdict(set)

    for record in manifest.records:
        _validate_record_fields(record, root, issues)
        if record.sample_id in by_id:
            _issue(issues, "duplicate_sample_id", "sample_id must be unique", record)
        else:
            by_id[record.sample_id] = record
        if SHA256_PATTERN.fullmatch(record.sha256):
            by_hash[record.sha256].append(record)
        group_splits[record.source_group_id].add(record.split)

    for records in by_hash.values():
        if len(records) > 1:
            labels = {record.label for record in records}
            code = "conflicting_duplicate_labels" if len(labels) > 1 else "duplicate_sha256"
            for record in records:
                _issue(issues, code, "image bytes are duplicated across manifest records", record)

    for group, splits in group_splits.items():
        if len(splits) > 1:
            _issue(
                issues,
                "source_group_leakage",
                f"source group {group!r} crosses splits: {', '.join(sorted(splits))}",
            )

    for record in manifest.records:
        if not record.parent_sample_id:
            continue
        parent = by_id.get(record.parent_sample_id)
        if parent is None:
            _issue(issues, "missing_parent", "parent_sample_id does not exist", record)
        elif parent.source_group_id != record.source_group_id or parent.split != record.split:
            _issue(
                issues,
                "parent_group_leakage",
                "parent and derived sample must share source group and split",
                record,
            )

    split_counts = Counter(record.split for record in manifest.records)
    label_counts = Counter(record.label for record in manifest.records)
    source_counts = Counter(record.source_type for record in manifest.records)
    for required_split in sorted(ALLOWED_SPLITS):
        if split_counts[required_split] == 0:
            _issue(
                issues,
                "empty_split",
                f"{required_split} split is empty",
                severity="warning",
            )
    for required_label in ("genuine", "fraudulent"):
        if label_counts[required_label] == 0:
            _issue(
                issues,
                "missing_core_label",
                f"controlled binary dataset has no {required_label} sample",
                severity="warning",
            )

    return ValidationReport(
        schema_version=MANIFEST_SCHEMA_VERSION,
        manifest_hash=manifest.manifest_hash,
        split_hash=manifest.split_hash,
        record_count=len(manifest.records),
        group_count=len(group_splits),
        split_counts=dict(split_counts),
        label_counts=dict(label_counts),
        source_type_counts=dict(source_counts),
        issues=tuple(issues),
    )
