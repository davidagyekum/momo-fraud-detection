"""Fail-closed, no-network dataset registration and validation primitives."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import sqlite3
import stat
import tempfile
import zipfile
from collections import Counter
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import IO, Final

from PIL import Image, UnidentifiedImageError

from momo_fdvs_ml.governance import GovernanceError, load_and_validate_registry

ACQUISITION_FOUNDATION_VERSION: Final = "dataset-acquisition-foundation-v1"
READINESS_SCHEMA_VERSION: Final = "dataset-acquisition-readiness-v1"
REQUEST_SCHEMA_VERSION: Final = "acquisition-request-v1"
MANIFEST_SCHEMA_VERSION: Final = "dataset-registration-manifest-v1"
VALIDATION_SPEC_VERSION: Final = "dataset-validation-spec-v1"
SHA256_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")
OPAQUE_REVIEWER_PATTERN: Final = re.compile(r"^REVIEWER_[A-F0-9]{12}$")
OPAQUE_PERMISSION_PATTERN: Final = re.compile(r"^PERMISSION_[A-F0-9]{12,64}$")
OPAQUE_TERMS_PATTERN: Final = re.compile(r"^(?:LICENCE|CONSENT)_[A-F0-9]{12,64}$")
MAX_ARCHIVE_MEMBERS: Final = 100_000
MAX_ARCHIVE_UNCOMPRESSED_BYTES: Final = 100 * 1024**3
DEFAULT_MAX_IMAGE_BYTES: Final = 50 * 1024**2
DEFAULT_MAX_IMAGE_DIMENSION: Final = 20_000
DEFAULT_MAX_IMAGE_PIXELS: Final = 100_000_000
NULL_MARKERS: Final = {"", "null", "none", "nan", "na", "n/a"}
READY_SPEC_STATUSES: Final = {"ready", "ready_after_governance_approval"}


class AcquisitionError(ValueError):
    """Raised when source governance, identity or validation fails closed."""


@dataclass(frozen=True)
class SourceInventory:
    source_sha256: str
    source_size_bytes: int
    file_count: int
    inventory_sha256: str


@dataclass(frozen=True)
class RegistrationOutputs:
    manifest_path: Path
    profile_path: Path
    manifest: dict[str, object]


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def _canonical_hash(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_object(path: Path, *, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AcquisitionError(f"unable to load {label}") from exc
    if not isinstance(value, dict):
        raise AcquisitionError(f"{label} must contain an object")
    return value


def _expect_exact_keys(payload: Mapping[str, object], expected: frozenset[str], label: str) -> None:
    missing = sorted(expected - set(payload))
    extra = sorted(set(payload) - expected)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if extra:
            details.append(f"unknown {', '.join(extra)}")
        raise AcquisitionError(f"{label} fields invalid: {'; '.join(details)}")


def _expect_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AcquisitionError(f"{label} must be a non-empty string")
    return value


def _expect_sha256(value: object, label: str) -> str:
    result = _expect_string(value, label)
    if SHA256_PATTERN.fullmatch(result) is None:
        raise AcquisitionError(f"{label} must be a lowercase SHA-256")
    return result


def _expect_positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise AcquisitionError(f"{label} must be a positive integer")
    return value


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, indent=2, sort_keys=True) + "\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _registry_entries(data_root: Path) -> tuple[dict[str, object], ...]:
    try:
        registry = load_and_validate_registry(data_root)
    except GovernanceError as exc:
        raise AcquisitionError(str(exc)) from exc
    values = registry["datasets"]
    if not isinstance(values, list):
        raise AcquisitionError("dataset registry shape is invalid")
    entries: list[dict[str, object]] = []
    for value in values:
        if not isinstance(value, dict):
            raise AcquisitionError("dataset registry entry is invalid")
        entries.append(value)
    return tuple(entries)


def _load_validation_spec(data_root: Path, dataset_id: str) -> dict[str, object]:
    spec = _load_object(
        data_root / "acquisition_specs" / f"{dataset_id}.json",
        label="dataset validation specification",
    )
    if spec.get("schema_version") != VALIDATION_SPEC_VERSION:
        raise AcquisitionError("unsupported dataset validation specification")
    if spec.get("dataset_id") != dataset_id:
        raise AcquisitionError("dataset validation specification ID mismatch")
    _expect_string(spec.get("status"), "validation specification status")
    _expect_string(spec.get("dataset_kind"), "dataset kind")
    return spec


def acquisition_readiness_report(data_root: Path) -> dict[str, object]:
    """Report exact fail-closed reasons without acquiring or opening source bytes."""

    sources: list[dict[str, object]] = []
    for entry in sorted(_registry_entries(data_root), key=lambda item: str(item["dataset_id"])):
        dataset_id = str(entry["dataset_id"])
        spec = _load_validation_spec(data_root, dataset_id)
        blockers: list[str] = []
        if entry["permission_status"] != "approved":
            blockers.append(f"permission_status:{entry['permission_status']}")
        if entry["licence_status"] not in {"verified", "not_applicable_private_consent"}:
            blockers.append(f"licence_status:{entry['licence_status']}")
        if spec["status"] not in READY_SPEC_STATUSES:
            blockers.append(f"validation_spec_status:{spec['status']}")
        if entry["acquisition_status"] == "quarantined":
            blockers.append("acquisition_status:quarantined")
        if dataset_id == "stfd" and entry["permission_status"] != "approved":
            blockers.append("written_access_approval_missing")
        if dataset_id == "ghana-private" and entry["permission_status"] != "approved":
            blockers.append("participant_consent_evidence_missing")
        sources.append(
            {
                "dataset_id": dataset_id,
                "required": entry["required"],
                "enabled": entry["enabled"],
                "acquisition_status": entry["acquisition_status"],
                "validation_spec_status": spec["status"],
                "eligible_for_local_registration": not blockers,
                "blockers": sorted(set(blockers)),
            }
        )
    return {
        "schema_version": READINESS_SCHEMA_VERSION,
        "foundation_version": ACQUISITION_FOUNDATION_VERSION,
        "source_count": len(sources),
        "eligible_source_count": sum(
            1 for source in sources if source["eligible_for_local_registration"] is True
        ),
        "blocked_source_count": sum(
            1 for source in sources if source["eligible_for_local_registration"] is False
        ),
        "sources": sources,
        "network_acquisition_executed": False,
        "source_bytes_opened": False,
        "training_executed": False,
    }


def readiness_markdown(report: Mapping[str, object]) -> str:
    sources = report.get("sources")
    if not isinstance(sources, list):
        raise AcquisitionError("readiness report sources are invalid")
    lines = [
        "# Dataset acquisition readiness",
        "",
        "> Safe metadata only. This report performs no download and grants no permission.",
        "",
        "| Dataset | Required | Eligible | Registry state | Blockers |",
        "|---|---:|---:|---|---|",
    ]
    for source in sources:
        if not isinstance(source, dict):
            raise AcquisitionError("readiness source is invalid")
        blockers = source.get("blockers")
        blocker_text = (
            ", ".join(str(item) for item in blockers) if isinstance(blockers, list) else ""
        )
        lines.append(
            "| {dataset} | {required} | {eligible} | {state} | {blockers} |".format(
                dataset=source["dataset_id"],
                required="yes" if source["required"] else "no",
                eligible="yes" if source["eligible_for_local_registration"] else "no",
                state=source["acquisition_status"],
                blockers=blocker_text or "none",
            )
        )
    lines.extend(
        [
            "",
            "Eligible: {eligible} / {total}.".format(
                eligible=report.get("eligible_source_count", 0),
                total=report.get("source_count", 0),
            ),
            "",
            "No source bytes were opened; acquisition and training are false.",
            "",
        ]
    )
    return "\n".join(lines)


def write_readiness_outputs(
    data_root: Path, *, report_path: Path, inventory_path: Path
) -> dict[str, object]:
    report = acquisition_readiness_report(data_root)
    _write_json_atomic(report_path, report)
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(readiness_markdown(report), encoding="utf-8", newline="\n")
    return report


REQUEST_FIELDS: Final = frozenset(
    {
        "schema_version",
        "dataset_id",
        "purpose",
        "reviewer_id",
        "permission_reference",
        "licence_reference",
        "source_kind",
        "source_path",
        "entrypoint",
        "expected_sha256",
        "expected_size_bytes",
        "expected_version",
        "created_at",
        "acknowledgements",
    }
)


def load_registration_request(path: Path) -> dict[str, object]:
    request = _load_object(path, label="registration request")
    _expect_exact_keys(request, REQUEST_FIELDS, "registration request")
    if request["schema_version"] != REQUEST_SCHEMA_VERSION:
        raise AcquisitionError("unsupported registration request version")
    for field in (
        "dataset_id",
        "purpose",
        "source_path",
        "expected_version",
        "created_at",
    ):
        _expect_string(request[field], field)
    if OPAQUE_REVIEWER_PATTERN.fullmatch(str(request["reviewer_id"])) is None:
        raise AcquisitionError("reviewer_id must be an opaque reviewer reference")
    if OPAQUE_PERMISSION_PATTERN.fullmatch(str(request["permission_reference"])) is None:
        raise AcquisitionError("permission_reference must be opaque")
    if OPAQUE_TERMS_PATTERN.fullmatch(str(request["licence_reference"])) is None:
        raise AcquisitionError("licence_reference must be opaque")
    if request["source_kind"] not in {"file", "directory"}:
        raise AcquisitionError("source_kind must be file or directory")
    if request["entrypoint"] is not None and not isinstance(request["entrypoint"], str):
        raise AcquisitionError("entrypoint must be a string or null")
    _expect_sha256(request["expected_sha256"], "expected_sha256")
    size = request["expected_size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size < 1:
        raise AcquisitionError("expected_size_bytes must be a positive integer")
    try:
        parsed = datetime.fromisoformat(str(request["created_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise AcquisitionError("created_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise AcquisitionError("created_at must include a timezone")
    acknowledgements = request["acknowledgements"]
    expected_ack = {
        "terms_reviewed",
        "no_redistribution",
        "private_storage",
        "version_verified",
    }
    if not isinstance(acknowledgements, dict) or set(acknowledgements) != expected_ack:
        raise AcquisitionError("acknowledgements must contain the exact required fields")
    if any(value is not True for value in acknowledgements.values()):
        raise AcquisitionError("all acquisition acknowledgements must be true")
    return request


def _safe_relative_name(name: str) -> PurePosixPath:
    normalized = PurePosixPath(name.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts or not normalized.parts:
        raise AcquisitionError("source contains an unsafe member path")
    return normalized


def _zip_inventory(path: Path) -> tuple[list[dict[str, object]], int]:
    records: list[dict[str, object]] = []
    total = 0
    normalized_names: set[str] = set()
    try:
        with zipfile.ZipFile(path) as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            if not infos or len(infos) > MAX_ARCHIVE_MEMBERS:
                raise AcquisitionError("archive member count is outside the allowed range")
            for info in infos:
                relative = _safe_relative_name(info.filename)
                normalized_name = relative.as_posix().casefold()
                if normalized_name in normalized_names:
                    raise AcquisitionError("archive contains duplicate normalized member paths")
                normalized_names.add(normalized_name)
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise AcquisitionError("archive symbolic links are prohibited")
                total += info.file_size
                if total > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                    raise AcquisitionError("archive uncompressed size exceeds the safety cap")
                digest = hashlib.sha256()
                with archive.open(info) as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                records.append(
                    {
                        "relative_name_sha256": hashlib.sha256(
                            relative.as_posix().encode("utf-8")
                        ).hexdigest(),
                        "sha256": digest.hexdigest(),
                        "size_bytes": info.file_size,
                    }
                )
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise AcquisitionError("unable to inspect source archive") from exc
    return sorted(records, key=lambda item: str(item["relative_name_sha256"])), total


def _directory_inventory(path: Path) -> tuple[list[dict[str, object]], int]:
    records: list[dict[str, object]] = []
    total = 0
    for child in sorted(path.rglob("*"), key=lambda value: value.as_posix()):
        if child.is_symlink():
            raise AcquisitionError("source directory symbolic links are prohibited")
        if not child.is_file():
            continue
        relative = child.relative_to(path).as_posix()
        size = child.stat().st_size
        total += size
        records.append(
            {
                "relative_name_sha256": hashlib.sha256(relative.encode("utf-8")).hexdigest(),
                "sha256": _file_hash(child),
                "size_bytes": size,
            }
        )
    if not records:
        raise AcquisitionError("source directory contains no files")
    return records, total


def source_inventory(path: Path, *, source_kind: str) -> SourceInventory:
    if source_kind == "file":
        if not path.is_file() or path.is_symlink():
            raise AcquisitionError("registered file source must be a regular file")
        size = path.stat().st_size
        if size < 1:
            raise AcquisitionError("registered source is empty")
        source_hash = _file_hash(path)
        if zipfile.is_zipfile(path):
            records, _ = _zip_inventory(path)
        else:
            records = [
                {
                    "relative_name_sha256": hashlib.sha256(b"source-file").hexdigest(),
                    "sha256": source_hash,
                    "size_bytes": size,
                }
            ]
        return SourceInventory(source_hash, size, len(records), _canonical_hash(records))
    if source_kind != "directory" or not path.is_dir() or path.is_symlink():
        raise AcquisitionError("registered directory source must be a regular directory")
    records, size = _directory_inventory(path)
    inventory_hash = _canonical_hash(records)
    return SourceInventory(inventory_hash, size, len(records), inventory_hash)


def _resolve_source(source_path: str, allowed_source_root: Path) -> Path:
    root = allowed_source_root.resolve(strict=True)
    source = Path(source_path)
    if not source.is_absolute():
        raise AcquisitionError("source_path must be absolute")
    try:
        resolved = source.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise AcquisitionError("source_path must stay inside the approved private root") from exc
    return resolved


@contextmanager
def _open_entrypoint(source: Path, request: Mapping[str, object]) -> Iterator[IO[bytes]]:
    entrypoint = request["entrypoint"]
    if source.is_dir():
        if not isinstance(entrypoint, str) or not entrypoint:
            raise AcquisitionError("directory transaction source requires an entrypoint")
        relative = _safe_relative_name(entrypoint)
        target = (source / Path(*relative.parts)).resolve(strict=True)
        try:
            target.relative_to(source.resolve(strict=True))
        except ValueError as exc:
            raise AcquisitionError("entrypoint leaves the source directory") from exc
        if not target.is_file() or target.is_symlink():
            raise AcquisitionError("entrypoint must be a regular file")
        with target.open("rb") as handle:
            yield handle
        return
    if zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            csv_names = [
                info.filename
                for info in archive.infolist()
                if not info.is_dir() and info.filename.lower().endswith(".csv")
            ]
            selected = entrypoint if isinstance(entrypoint, str) and entrypoint else None
            if selected is None:
                if len(csv_names) != 1:
                    raise AcquisitionError("archive requires an unambiguous CSV entrypoint")
                selected = csv_names[0]
            _safe_relative_name(selected)
            if selected not in csv_names:
                raise AcquisitionError("CSV entrypoint is not present in the archive")
            with archive.open(selected) as handle:
                yield handle
        return
    if entrypoint not in {None, ""}:
        raise AcquisitionError("raw file source cannot specify an archive entrypoint")
    with source.open("rb") as handle:
        yield handle


def _scan_transaction_csv(
    source: Path, request: Mapping[str, object], spec: Mapping[str, object]
) -> tuple[dict[str, object], list[str]]:
    required = spec.get("required_columns")
    if (
        not isinstance(required, list)
        or not required
        or not all(isinstance(item, str) and item for item in required)
    ):
        raise AcquisitionError("transaction validation specification lacks raw columns")
    label_column = _expect_string(spec.get("label_column"), "label_column")
    positive_values = spec.get("positive_values")
    if not isinstance(positive_values, list) or not positive_values:
        raise AcquisitionError("transaction validation specification lacks positive values")
    positive_set = {str(value) for value in positive_values}
    step_column = spec.get("step_column")
    amount_column = str(spec.get("amount_column", "amount"))
    rows = 0
    positives = 0
    null_cells = 0
    invalid_amounts = 0
    invalid_labels = 0
    duplicates = 0
    steps: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="momo-fdvs-pr13-") as temporary:
        database = Path(temporary) / "row-hashes.sqlite3"
        connection = sqlite3.connect(database)
        try:
            connection.execute("CREATE TABLE row_hashes (value TEXT PRIMARY KEY)")
            with _open_entrypoint(source, request) as binary:
                text = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
                reader = csv.DictReader(text)
                fields = reader.fieldnames
                if fields is None or len(fields) != len(set(fields)):
                    raise AcquisitionError("transaction CSV header is missing or duplicated")
                missing = sorted(set(required) - set(fields))
                if missing:
                    raise AcquisitionError(
                        f"transaction CSV is missing required columns: {', '.join(missing)}"
                    )
                for row in reader:
                    rows += 1
                    values = {key: row.get(key, "") for key in fields}
                    null_cells += sum(
                        1 for value in values.values() if value.strip().lower() in NULL_MARKERS
                    )
                    label = values[label_column].strip()
                    if label in positive_set:
                        positives += 1
                    elif label not in {"0", "false", "False"}:
                        invalid_labels += 1
                    try:
                        amount = float(values[amount_column])
                        if amount < 0:
                            invalid_amounts += 1
                    except (KeyError, ValueError):
                        invalid_amounts += 1
                    if isinstance(step_column, str) and step_column:
                        steps.add(values.get(step_column, ""))
                    row_hash = _canonical_hash(values)
                    try:
                        connection.execute("INSERT INTO row_hashes(value) VALUES (?)", (row_hash,))
                    except sqlite3.IntegrityError:
                        duplicates += 1
            connection.commit()
        finally:
            connection.close()
    reasons: list[str] = []
    expected = {
        "expected_row_count": rows,
        "expected_positive_count": positives,
        "expected_step_count": len(steps),
    }
    for key, observed in expected.items():
        configured = spec.get(key)
        if isinstance(configured, int) and configured != observed:
            reasons.append(f"{key}_mismatch")
    if rows == 0:
        reasons.append("empty_transaction_dataset")
    if positives == 0:
        reasons.append("empty_positive_target")
    if invalid_labels:
        reasons.append("invalid_target_values")
    if invalid_amounts:
        reasons.append("invalid_amount_values")
    if null_cells:
        reasons.append("null_values_present")
    if duplicates:
        reasons.append("duplicate_rows_present")
    forbidden = spec.get("forbidden_primary_benchmark_columns", [])
    return (
        {
            "dataset_kind": "transaction_csv",
            "row_count": rows,
            "positive_count": positives,
            "step_count": len(steps),
            "null_cell_count": null_cells,
            "invalid_amount_count": invalid_amounts,
            "invalid_label_count": invalid_labels,
            "duplicate_row_count": duplicates,
            "forbidden_primary_benchmark_columns": forbidden,
        },
        sorted(set(reasons)),
    )


def _iter_image_payloads(
    source: Path, allowed_extensions: set[str], *, max_image_bytes: int
) -> Iterator[tuple[str, bytes | None, int]]:
    if source.is_dir():
        for child in sorted(source.rglob("*"), key=lambda value: value.as_posix()):
            if child.is_symlink():
                raise AcquisitionError("source directory symbolic links are prohibited")
            if child.is_file() and child.suffix.lower() in allowed_extensions:
                size = child.stat().st_size
                yield (
                    child.relative_to(source).as_posix(),
                    child.read_bytes() if size <= max_image_bytes else None,
                    size,
                )
        return
    if not zipfile.is_zipfile(source):
        if source.suffix.lower() in allowed_extensions:
            size = source.stat().st_size
            yield "source-image", source.read_bytes() if size <= max_image_bytes else None, size
            return
        raise AcquisitionError("image collection must be a directory, ZIP or supported image")
    with zipfile.ZipFile(source) as archive:
        for info in sorted(archive.infolist(), key=lambda value: value.filename):
            if info.is_dir():
                continue
            relative = _safe_relative_name(info.filename)
            if relative.suffix.lower() in allowed_extensions:
                with archive.open(info) as handle:
                    payload = handle.read() if info.file_size <= max_image_bytes else None
                    yield relative.as_posix(), payload, info.file_size


def deterministic_subset_ids(member_names: list[str], *, seed: int, count: int) -> list[str]:
    if count < 0 or count > len(member_names):
        raise AcquisitionError("deterministic subset count is invalid")
    ranked = sorted(
        member_names,
        key=lambda name: hashlib.sha256(f"{seed}:{name}".encode()).hexdigest(),
    )
    return [hashlib.sha256(name.encode("utf-8")).hexdigest() for name in ranked[:count]]


def _scan_parallel_mask_collection(
    source: Path,
    spec: Mapping[str, object],
    *,
    extensions: set[str],
    max_image_bytes: int,
    max_dimension: int,
    max_pixels: int,
) -> tuple[dict[str, object], list[str]]:
    if not source.is_dir():
        raise AcquisitionError("parallel mask collection must be an extracted directory")
    raw_categories = spec.get("tampering_directories")
    if (
        not isinstance(raw_categories, list)
        or not raw_categories
        or not all(isinstance(value, str) and value for value in raw_categories)
    ):
        raise AcquisitionError("parallel mask collection lacks category directories")
    categories = [str(value) for value in raw_categories]
    image_directory_name = _expect_string(spec.get("image_directory_name"), "image_directory_name")
    mask_directory_name = _expect_string(spec.get("mask_directory_name"), "mask_directory_name")
    raw_expected_counts = spec.get("expected_pair_counts")
    if not isinstance(raw_expected_counts, dict) or set(raw_expected_counts) != set(categories):
        raise AcquisitionError("parallel mask collection pair-count contract is incomplete")
    expected_counts = {
        category: _expect_positive_int(raw_expected_counts[category], category)
        for category in categories
    }
    expected_soft_masks = _expect_positive_int(
        spec.get("expected_soft_mask_count"), "expected_soft_mask_count"
    )
    expected_soft_mask_pixels = _expect_positive_int(
        spec.get("expected_soft_mask_pixel_count"), "expected_soft_mask_pixel_count"
    )
    soft_mask_threshold = _expect_positive_int(
        spec.get("soft_mask_threshold"), "soft_mask_threshold"
    )
    if soft_mask_threshold > 254:
        raise AcquisitionError("soft mask threshold must be between 1 and 254")
    grouping_strategy = _expect_string(spec.get("grouping_strategy"), "grouping_strategy")
    if grouping_strategy != "single_external_pretraining_corpus_group":
        raise AcquisitionError("parallel mask collection grouping strategy is unsupported")

    reasons: list[str] = []
    category_pair_counts: dict[str, int] = {}
    dimensions: Counter[str] = Counter()
    image_modes: Counter[str] = Counter()
    mask_modes: Counter[str] = Counter()
    image_hashes: Counter[str] = Counter()
    mask_hashes: Counter[str] = Counter()
    original_names: list[str] = []
    original_count = 0
    mask_count = 0
    paired_count = 0
    missing_mask_count = 0
    orphan_mask_count = 0
    image_decode_failures = 0
    mask_decode_failures = 0
    oversized_files = 0
    zero_dimension = 0
    dimension_violations = 0
    dimension_mismatches = 0
    soft_mask_count = 0
    soft_mask_pixel_count = 0
    blank_mask_count = 0

    for category in categories:
        matches = sorted(
            (
                path
                for path in source.rglob(category)
                if path.is_dir()
                and (path / image_directory_name).is_dir()
                and (path / mask_directory_name).is_dir()
            ),
            key=lambda value: value.as_posix(),
        )
        if len(matches) != 1:
            reasons.append("category_directory_layout_mismatch")
            category_pair_counts[category] = 0
            continue
        category_root = matches[0]
        image_root = category_root / image_directory_name
        mask_root = category_root / mask_directory_name
        if not image_root.is_dir() or not mask_root.is_dir():
            reasons.append("parallel_mask_directory_layout_mismatch")
            category_pair_counts[category] = 0
            continue
        image_paths = {
            path.name.casefold(): path
            for path in image_root.iterdir()
            if path.is_file() and path.suffix.lower() in extensions
        }
        mask_paths = {
            path.name.casefold(): path
            for path in mask_root.iterdir()
            if path.is_file() and path.suffix.lower() in extensions
        }
        original_count += len(image_paths)
        mask_count += len(mask_paths)
        missing = set(image_paths) - set(mask_paths)
        orphaned = set(mask_paths) - set(image_paths)
        missing_mask_count += len(missing)
        orphan_mask_count += len(orphaned)
        shared = sorted(set(image_paths) & set(mask_paths))
        category_pair_counts[category] = len(shared)
        if len(shared) != expected_counts[category]:
            reasons.append("expected_category_pair_count_mismatch")

        for normalized_name in shared:
            image_path = image_paths[normalized_name]
            mask_path = mask_paths[normalized_name]
            if image_path.is_symlink() or mask_path.is_symlink():
                raise AcquisitionError("source directory symbolic links are prohibited")
            original_names.append(f"{category}/{image_directory_name}/{image_path.name}")
            image_size_bytes = image_path.stat().st_size
            mask_size_bytes = mask_path.stat().st_size
            if image_size_bytes > max_image_bytes or mask_size_bytes > max_image_bytes:
                oversized_files += 1
                continue
            try:
                with image_path.open("rb") as stream:
                    image_hashes[hashlib.file_digest(stream, "sha256").hexdigest()] += 1
                with Image.open(image_path) as image:
                    image.load()
                    image_size = image.size
                    image_modes[image.mode] += 1
                    width, height = image_size
                    dimensions[f"{width}x{height}"] += 1
                    if width < 1 or height < 1:
                        zero_dimension += 1
                    if (
                        width > max_dimension
                        or height > max_dimension
                        or width * height > max_pixels
                    ):
                        dimension_violations += 1
            except (UnidentifiedImageError, OSError, ValueError):
                image_decode_failures += 1
                continue
            try:
                with mask_path.open("rb") as stream:
                    mask_hashes[hashlib.file_digest(stream, "sha256").hexdigest()] += 1
                with Image.open(mask_path) as mask:
                    mask.load()
                    mask_modes[mask.mode] += 1
                    mask_size = mask.size
                    histogram = mask.convert("L").histogram()
                    nonbinary_pixels = sum(histogram[1:255])
                    if nonbinary_pixels:
                        soft_mask_count += 1
                        soft_mask_pixel_count += nonbinary_pixels
                    if histogram[0] == 0 or histogram[255] == 0:
                        blank_mask_count += 1
            except (UnidentifiedImageError, OSError, ValueError):
                mask_decode_failures += 1
                continue
            if image_size != mask_size:
                dimension_mismatches += 1
            paired_count += 1

    if original_count == 0:
        reasons.append("empty_image_collection")
    if missing_mask_count:
        reasons.append("missing_masks")
    if orphan_mask_count:
        reasons.append("orphan_masks")
    if image_decode_failures:
        reasons.append("image_decode_failures")
    if mask_decode_failures:
        reasons.append("mask_decode_failures")
    if oversized_files:
        reasons.append("oversized_image_files")
    if zero_dimension:
        reasons.append("invalid_image_dimensions")
    if dimension_violations:
        reasons.append("image_dimension_cap_exceeded")
    if dimension_mismatches:
        reasons.append("mask_dimension_mismatch")
    if blank_mask_count:
        reasons.append("blank_masks")
    if soft_mask_count != expected_soft_masks:
        reasons.append("soft_mask_count_mismatch")
    if soft_mask_pixel_count != expected_soft_mask_pixels:
        reasons.append("soft_mask_pixel_count_mismatch")
    duplicate_image_occurrences = sum(count - 1 for count in image_hashes.values() if count > 1)
    duplicate_mask_occurrences = sum(count - 1 for count in mask_hashes.values() if count > 1)
    if duplicate_image_occurrences:
        reasons.append("duplicate_image_payloads")
    if duplicate_mask_occurrences:
        reasons.append("duplicate_mask_payloads")
    subset_count = min(100, len(original_names))
    return (
        {
            "dataset_kind": str(spec["dataset_kind"]),
            "image_count": original_count + mask_count,
            "original_image_count": original_count,
            "mask_count": mask_count,
            "paired_image_mask_count": paired_count,
            "missing_mask_count": missing_mask_count,
            "orphan_mask_count": orphan_mask_count,
            "image_decode_failure_count": image_decode_failures,
            "mask_decode_failure_count": mask_decode_failures,
            "zero_dimension_count": zero_dimension,
            "oversized_file_count": oversized_files,
            "dimension_violation_count": dimension_violations,
            "mask_dimension_mismatch_count": dimension_mismatches,
            "blank_mask_count": blank_mask_count,
            "soft_mask_count": soft_mask_count,
            "soft_mask_pixel_count": soft_mask_pixel_count,
            "soft_mask_threshold": soft_mask_threshold,
            "source_masks_modified": False,
            "derived_mask_policy": "rendered_luminance_threshold_train_only",
            "exact_duplicate_image_occurrence_count": duplicate_image_occurrences,
            "exact_duplicate_mask_occurrence_count": duplicate_mask_occurrences,
            "category_pair_counts": dict(sorted(category_pair_counts.items())),
            "dimension_counts": dict(sorted(dimensions.items())),
            "image_mode_counts": dict(sorted(image_modes.items())),
            "mask_mode_counts": dict(sorted(mask_modes.items())),
            "grouping_strategy": grouping_strategy,
            "source_group_count": 1,
            "split_usage": "external_pretraining_train_only",
            "internal_evaluation_allowed": False,
            "deterministic_subset_seed": 20260811,
            "deterministic_subset_ids": deterministic_subset_ids(
                original_names, seed=20260811, count=subset_count
            ),
        },
        sorted(set(reasons)),
    )


def _scan_image_collection(
    source: Path, spec: Mapping[str, object]
) -> tuple[dict[str, object], list[str]]:
    raw_extensions = spec.get("allowed_image_extensions")
    if not isinstance(raw_extensions, list) or not raw_extensions:
        raise AcquisitionError("image validation specification lacks extensions")
    extensions = {str(value).lower() for value in raw_extensions}
    max_image_bytes = _expect_positive_int(
        spec.get("max_image_bytes", DEFAULT_MAX_IMAGE_BYTES), "max_image_bytes"
    )
    max_dimension = _expect_positive_int(
        spec.get("max_image_dimension", DEFAULT_MAX_IMAGE_DIMENSION),
        "max_image_dimension",
    )
    max_pixels = _expect_positive_int(
        spec.get("max_image_pixels", DEFAULT_MAX_IMAGE_PIXELS), "max_image_pixels"
    )
    if spec.get("pairing_strategy") == "parallel_category_directories":
        return _scan_parallel_mask_collection(
            source,
            spec,
            extensions=extensions,
            max_image_bytes=max_image_bytes,
            max_dimension=max_dimension,
            max_pixels=max_pixels,
        )
    image_count = 0
    decode_failures = 0
    zero_dimension = 0
    oversized_files = 0
    dimension_violations = 0
    dimensions: dict[str, int] = {}
    names: list[str] = []
    decoded_dimensions: dict[str, tuple[int, int]] = {}
    for name, payload, _size in _iter_image_payloads(
        source, extensions, max_image_bytes=max_image_bytes
    ):
        image_count += 1
        names.append(name)
        if payload is None:
            oversized_files += 1
            continue
        try:
            with Image.open(io.BytesIO(payload)) as image:
                image.verify()
                width, height = image.size
                decoded_dimensions[name] = (width, height)
                if width < 1 or height < 1:
                    zero_dimension += 1
                if width > max_dimension or height > max_dimension or width * height > max_pixels:
                    dimension_violations += 1
                dimension_key = f"{width}x{height}"
                dimensions[dimension_key] = dimensions.get(dimension_key, 0) + 1
        except (UnidentifiedImageError, OSError, ValueError):
            decode_failures += 1
    reasons: list[str] = []
    if image_count == 0:
        reasons.append("empty_image_collection")
    if decode_failures:
        reasons.append("image_decode_failures")
    if zero_dimension:
        reasons.append("invalid_image_dimensions")
    if oversized_files:
        reasons.append("oversized_image_files")
    if dimension_violations:
        reasons.append("image_dimension_cap_exceeded")
    mask_count = 0
    original_count = image_count
    if spec.get("requires_masks") is True:
        mask_suffix = spec.get("mask_suffix")
        if not isinstance(mask_suffix, str) or not mask_suffix:
            raise AcquisitionError("mask-required specification must define mask_suffix")
        originals: dict[str, tuple[int, int]] = {}
        masks: dict[str, tuple[int, int]] = {}
        original_names: list[str] = []
        for name, size in decoded_dimensions.items():
            path = PurePosixPath(name)
            if path.stem.endswith(mask_suffix):
                base_stem = path.stem[: -len(mask_suffix)]
                key = (path.parent / base_stem).as_posix()
                masks[key] = size
            else:
                key = (path.parent / path.stem).as_posix()
                originals[key] = size
                original_names.append(name)
        missing_masks = sorted(set(originals) - set(masks))
        orphan_masks = sorted(set(masks) - set(originals))
        mismatched = sorted(
            key for key in set(originals) & set(masks) if originals[key] != masks[key]
        )
        if missing_masks:
            reasons.append("missing_masks")
        if orphan_masks:
            reasons.append("orphan_masks")
        if mismatched:
            reasons.append("mask_dimension_mismatch")
        mask_count = len(masks)
        original_count = len(originals)
        names = original_names
    subset_count = min(100, len(names))
    return (
        {
            "dataset_kind": str(spec["dataset_kind"]),
            "image_count": image_count,
            "decode_failure_count": decode_failures,
            "zero_dimension_count": zero_dimension,
            "oversized_file_count": oversized_files,
            "dimension_violation_count": dimension_violations,
            "original_image_count": original_count,
            "mask_count": mask_count,
            "dimension_counts": dict(sorted(dimensions.items())),
            "deterministic_subset_seed": 20260811,
            "deterministic_subset_ids": deterministic_subset_ids(
                names, seed=20260811, count=subset_count
            ),
        },
        sorted(set(reasons)),
    )


def _eligible_entry(
    entries: tuple[dict[str, object], ...], request: Mapping[str, object]
) -> dict[str, object]:
    dataset_id = str(request["dataset_id"])
    try:
        entry = next(value for value in entries if value["dataset_id"] == dataset_id)
    except StopIteration as exc:
        raise AcquisitionError("registration request dataset is not canonical") from exc
    if entry["permission_status"] != "approved":
        raise AcquisitionError(f"{dataset_id} permission is not approved")
    if entry["licence_status"] not in {"verified", "not_applicable_private_consent"}:
        raise AcquisitionError(f"{dataset_id} licence/consent state is not verified")
    purposes = entry["allowed_purposes"]
    if not isinstance(purposes, list) or request["purpose"] not in purposes:
        raise AcquisitionError("requested purpose is not permitted by the registry")
    if request["expected_version"] != entry["version"]:
        raise AcquisitionError("requested version does not match the registry")
    return entry


def _validate_registration_manifest(manifest: Mapping[str, object]) -> None:
    fields = frozenset(
        {
            "schema_version",
            "dataset_id",
            "dataset_version",
            "status",
            "created_at",
            "source_kind",
            "source_sha256",
            "source_size_bytes",
            "file_count",
            "inventory_sha256",
            "request_sha256",
            "validation_spec_sha256",
            "validation_summary",
            "quarantine_reasons",
            "network_acquisition_executed",
            "source_bytes_committed",
            "promotable_for_training",
        }
    )
    _expect_exact_keys(manifest, fields, "registration manifest")
    if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise AcquisitionError("unsupported registration manifest version")
    if manifest["status"] not in {"registered", "quarantined"}:
        raise AcquisitionError("invalid registration manifest status")
    for field in ("source_sha256", "inventory_sha256", "request_sha256", "validation_spec_sha256"):
        _expect_sha256(manifest[field], field)
    if any(
        manifest[field] is not False
        for field in (
            "network_acquisition_executed",
            "source_bytes_committed",
            "promotable_for_training",
        )
    ):
        raise AcquisitionError("registration manifest contains unsafe execution flags")


def safe_registration_profile(
    manifest: Mapping[str, object],
    registry_entry: Mapping[str, object],
    *,
    include_members: bool = False,
) -> dict[str, object]:
    _validate_registration_manifest(manifest)
    if include_members:
        raise AcquisitionError("member-level export is prohibited from safe profiles")
    return {
        "schema_version": "dataset-safe-profile-v1",
        "dataset_id": manifest["dataset_id"],
        "dataset_version": manifest["dataset_version"],
        "status": manifest["status"],
        "data_classification": registry_entry["data_classification"],
        "redistribution": registry_entry["redistribution"],
        "source_sha256": manifest["source_sha256"],
        "source_size_bytes": manifest["source_size_bytes"],
        "file_count": manifest["file_count"],
        "inventory_sha256": manifest["inventory_sha256"],
        "validation_summary": manifest["validation_summary"],
        "quarantine_reasons": manifest["quarantine_reasons"],
        "contains_source_paths": False,
        "contains_member_names": False,
        "network_acquisition_executed": False,
        "training_executed": False,
        "promotable_for_training": False,
    }


def register_local_source(
    *,
    data_root: Path,
    request_path: Path,
    allowed_source_root: Path,
    manifest_path: Path,
    profile_path: Path,
) -> RegistrationOutputs:
    """Register authorized local bytes; never downloads, extracts, moves or deletes them."""

    request = load_registration_request(request_path)
    entries = _registry_entries(data_root)
    entry = _eligible_entry(entries, request)
    dataset_id = str(request["dataset_id"])
    spec = _load_validation_spec(data_root, dataset_id)
    if spec["status"] not in READY_SPEC_STATUSES:
        raise AcquisitionError(f"{dataset_id} validation specification is not ready")
    source = _resolve_source(str(request["source_path"]), allowed_source_root)
    inventory = source_inventory(source, source_kind=str(request["source_kind"]))
    quarantine: list[str] = []
    if inventory.source_sha256 != request["expected_sha256"]:
        quarantine.append("source_sha256_mismatch")
    if inventory.source_size_bytes != request["expected_size_bytes"]:
        quarantine.append("source_size_mismatch")
    dataset_kind = str(spec["dataset_kind"])
    if dataset_kind == "transaction_csv":
        validation, validation_reasons = _scan_transaction_csv(source, request, spec)
    elif dataset_kind in {"image_collection", "private_image_collection"}:
        validation, validation_reasons = _scan_image_collection(source, spec)
    else:
        raise AcquisitionError("unsupported dataset validation kind")
    quarantine.extend(validation_reasons)
    manifest: dict[str, object] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "dataset_version": request["expected_version"],
        "status": "quarantined" if quarantine else "registered",
        "created_at": request["created_at"],
        "source_kind": request["source_kind"],
        "source_sha256": inventory.source_sha256,
        "source_size_bytes": inventory.source_size_bytes,
        "file_count": inventory.file_count,
        "inventory_sha256": inventory.inventory_sha256,
        "request_sha256": _canonical_hash(request),
        "validation_spec_sha256": _canonical_hash(spec),
        "validation_summary": validation,
        "quarantine_reasons": sorted(set(quarantine)),
        "network_acquisition_executed": False,
        "source_bytes_committed": False,
        "promotable_for_training": False,
    }
    _validate_registration_manifest(manifest)
    profile = safe_registration_profile(manifest, entry)
    _write_json_atomic(manifest_path, manifest)
    _write_json_atomic(profile_path, profile)
    return RegistrationOutputs(manifest_path, profile_path, manifest)


def load_registration_manifest(path: Path) -> dict[str, object]:
    manifest = _load_object(path, label="registration manifest")
    _validate_registration_manifest(manifest)
    return manifest
