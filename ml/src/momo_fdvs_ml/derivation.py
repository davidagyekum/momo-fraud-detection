"""Deterministic, local-only transaction dataset derivation primitives."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sqlite3
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final, cast

REQUEST_SCHEMA_VERSION: Final = "transaction-deduplication-request-v1"
MANIFEST_SCHEMA_VERSION: Final = "transaction-deduplication-manifest-v1"
TRANSFORMATION_VERSION: Final = "exact-row-first-occurrence-v1"
SHA256_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")
REQUEST_FIELDS: Final = frozenset(
    {
        "schema_version",
        "dataset_id",
        "source_path",
        "expected_source_sha256",
        "expected_source_size_bytes",
        "source_dataset_version",
        "derived_dataset_version",
        "required_columns",
        "label_column",
        "positive_values",
        "created_at",
        "decision_reference",
        "transformation_version",
        "acknowledgements",
    }
)
ACKNOWLEDGEMENT_FIELDS: Final = frozenset(
    {"preserve_source", "private_output", "no_splits", "no_training"}
)
MANIFEST_FIELDS: Final = frozenset(
    {
        "schema_version",
        "transformation_version",
        "dataset_id",
        "source_dataset_version",
        "derived_dataset_version",
        "created_at",
        "source_sha256",
        "source_size_bytes",
        "output_sha256",
        "output_size_bytes",
        "header_sha256",
        "source_row_count",
        "output_row_count",
        "removed_duplicate_row_count",
        "duplicate_group_count",
        "max_duplicate_group_size",
        "source_positive_count",
        "output_positive_count",
        "removed_positive_count",
        "preserved_row_policy",
        "source_bytes_modified",
        "output_bytes_committed",
        "network_acquisition_executed",
        "splits_created",
        "training_executed",
        "promotable_for_training",
    }
)


class DerivationError(ValueError):
    """Raised when a governed dataset derivation fails closed."""


@dataclass(frozen=True)
class DeduplicationOutputs:
    """Paths and safe manifest emitted by a successful derivation."""

    output_path: Path
    manifest_path: Path
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


def _expect_exact_keys(payload: Mapping[str, object], expected: frozenset[str], label: str) -> None:
    missing = sorted(expected - set(payload))
    extra = sorted(set(payload) - expected)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if extra:
            details.append(f"unknown {', '.join(extra)}")
        raise DerivationError(f"{label} fields invalid: {'; '.join(details)}")


def _expect_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DerivationError(f"{label} must be a non-empty string")
    return value


def _expect_sha256(value: object, label: str) -> str:
    result = _expect_string(value, label)
    if SHA256_PATTERN.fullmatch(result) is None:
        raise DerivationError(f"{label} must be a lowercase SHA-256")
    return result


def _expect_positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise DerivationError(f"{label} must be a positive integer")
    return value


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_deduplication_request(path: Path) -> dict[str, object]:
    """Load and strictly validate a private derivation request."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DerivationError("unable to load deduplication request") from exc
    if not isinstance(payload, dict):
        raise DerivationError("deduplication request must contain an object")
    _expect_exact_keys(payload, REQUEST_FIELDS, "deduplication request")
    if payload["schema_version"] != REQUEST_SCHEMA_VERSION:
        raise DerivationError("unsupported deduplication request version")
    for field in (
        "dataset_id",
        "source_path",
        "source_dataset_version",
        "derived_dataset_version",
        "label_column",
        "created_at",
    ):
        _expect_string(payload[field], field)
    if payload["derived_dataset_version"] == payload["source_dataset_version"]:
        raise DerivationError("derived_dataset_version must differ from the official version")
    _expect_sha256(payload["expected_source_sha256"], "expected_source_sha256")
    _expect_positive_int(payload["expected_source_size_bytes"], "expected_source_size_bytes")
    if payload["decision_reference"] != "ADR-027":
        raise DerivationError("deduplication request requires ADR-027")
    if payload["transformation_version"] != TRANSFORMATION_VERSION:
        raise DerivationError("unsupported deduplication transformation")
    required = payload["required_columns"]
    if (
        not isinstance(required, list)
        or not required
        or not all(isinstance(value, str) and value for value in required)
        or len(required) != len(set(required))
    ):
        raise DerivationError("required_columns must be unique non-empty strings")
    if payload["label_column"] not in required:
        raise DerivationError("label_column must be present in required_columns")
    positive_values = payload["positive_values"]
    if (
        not isinstance(positive_values, list)
        or not positive_values
        or not all(isinstance(value, str) for value in positive_values)
    ):
        raise DerivationError("positive_values must be a non-empty string list")
    acknowledgements = payload["acknowledgements"]
    if not isinstance(acknowledgements, dict):
        raise DerivationError("acknowledgements must contain an object")
    _expect_exact_keys(acknowledgements, ACKNOWLEDGEMENT_FIELDS, "acknowledgements")
    if any(acknowledgements[field] is not True for field in ACKNOWLEDGEMENT_FIELDS):
        raise DerivationError("all deduplication acknowledgements must be true")
    try:
        created = datetime.fromisoformat(str(payload["created_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise DerivationError("created_at must be an ISO-8601 timestamp") from exc
    if created.tzinfo is None:
        raise DerivationError("created_at must include a timezone")
    return payload


def _resolve_source(path_value: object, allowed_root: Path) -> Path:
    root = allowed_root.resolve(strict=True)
    source = Path(_expect_string(path_value, "source_path"))
    if not source.is_absolute():
        raise DerivationError("source_path must be absolute")
    try:
        resolved = source.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise DerivationError("source_path must stay inside the approved private root") from exc
    if not resolved.is_file() or resolved.is_symlink():
        raise DerivationError("source_path must identify a regular file")
    return resolved


def _resolve_output(path: Path, allowed_root: Path, source: Path) -> Path:
    root = allowed_root.resolve(strict=True)
    if not path.is_absolute():
        raise DerivationError("output_path must be absolute")
    try:
        parent = path.parent.resolve(strict=True)
        parent.relative_to(root)
    except (OSError, ValueError) as exc:
        raise DerivationError("output_path must stay inside the approved private root") from exc
    resolved = parent / path.name
    if resolved == source:
        raise DerivationError("output_path must not overwrite the official source")
    if resolved.exists() or resolved.is_symlink():
        raise DerivationError("output_path must not already exist")
    if resolved.suffix.lower() != ".csv":
        raise DerivationError("output_path must use the .csv extension")
    return resolved


def _validate_manifest(manifest: Mapping[str, object]) -> None:
    _expect_exact_keys(manifest, MANIFEST_FIELDS, "deduplication manifest")
    if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise DerivationError("unsupported deduplication manifest version")
    for field in ("source_sha256", "output_sha256", "header_sha256"):
        _expect_sha256(manifest[field], field)
    if any(
        manifest[field] is not False
        for field in (
            "source_bytes_modified",
            "output_bytes_committed",
            "network_acquisition_executed",
            "splits_created",
            "training_executed",
            "promotable_for_training",
        )
    ):
        raise DerivationError("deduplication manifest contains unsafe execution flags")
    integer_fields = (
        "source_size_bytes",
        "output_size_bytes",
        "source_row_count",
        "output_row_count",
        "removed_duplicate_row_count",
        "duplicate_group_count",
        "max_duplicate_group_size",
        "source_positive_count",
        "output_positive_count",
        "removed_positive_count",
    )
    if any(
        isinstance(manifest[field], bool)
        or not isinstance(manifest[field], int)
        or manifest[field] < 0  # type: ignore[operator]
        for field in integer_fields
    ):
        raise DerivationError("deduplication manifest counts must be non-negative integers")
    counts = {field: cast(int, manifest[field]) for field in integer_fields}
    source_rows = counts["source_row_count"]
    output_rows = counts["output_row_count"]
    removed_rows = counts["removed_duplicate_row_count"]
    if output_rows < 1 or removed_rows < 1 or source_rows - output_rows != removed_rows:
        raise DerivationError("deduplication manifest row counts are inconsistent")
    if counts["duplicate_group_count"] < 1 or counts["max_duplicate_group_size"] < 2:
        raise DerivationError("deduplication manifest duplicate counts are inconsistent")
    if (
        counts["source_positive_count"] - counts["output_positive_count"]
        != counts["removed_positive_count"]
    ):
        raise DerivationError("deduplication manifest positive counts are inconsistent")


def load_deduplication_manifest(path: Path) -> dict[str, object]:
    """Load and validate a safe committed derivation manifest."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DerivationError("unable to load deduplication manifest") from exc
    if not isinstance(payload, dict):
        raise DerivationError("deduplication manifest must contain an object")
    _validate_manifest(payload)
    return payload


def derive_deduplicated_transactions(
    *,
    request_path: Path,
    allowed_source_root: Path,
    allowed_output_root: Path,
    output_path: Path,
    manifest_path: Path,
) -> DeduplicationOutputs:
    """Create an atomic first-occurrence CSV while preserving official source bytes."""

    request = load_deduplication_request(request_path)
    source = _resolve_source(request["source_path"], allowed_source_root)
    output = _resolve_output(output_path, allowed_output_root, source)
    source_size = source.stat().st_size
    source_sha256 = _file_hash(source)
    if source_sha256 != request["expected_source_sha256"]:
        raise DerivationError("official source SHA-256 does not match the request")
    if source_size != request["expected_source_size_bytes"]:
        raise DerivationError("official source byte size does not match the request")

    required_value = cast(list[object], request["required_columns"])
    positive_value = cast(list[object], request["positive_values"])
    required = [str(value) for value in required_value]
    label_column = str(request["label_column"])
    label_index = required.index(label_column)
    positive_set = {str(value) for value in positive_value}
    source_rows = output_rows = source_positives = output_positives = 0
    temporary_output = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        with tempfile.TemporaryDirectory(prefix="momo-fdvs-dedup-") as temporary:
            database = Path(temporary) / "seen.sqlite3"
            connection = sqlite3.connect(database)
            try:
                connection.execute(
                    "CREATE TABLE seen (value TEXT PRIMARY KEY, occurrences INTEGER NOT NULL)"
                )
                with (
                    source.open("r", encoding="utf-8-sig", newline="") as source_handle,
                    temporary_output.open("x", encoding="utf-8", newline="") as output_handle,
                ):
                    reader = csv.DictReader(source_handle)
                    if reader.fieldnames != required:
                        raise DerivationError("source CSV header does not match required_columns")
                    writer = csv.writer(output_handle, lineterminator="\n")
                    writer.writerow(required)
                    for row in reader:
                        source_rows += 1
                        values = [row.get(column, "") for column in required]
                        is_positive = values[label_index].strip() in positive_set
                        source_positives += int(is_positive)
                        row_hash = hashlib.sha256(_canonical_json(values)).hexdigest()
                        cursor = connection.execute(
                            "INSERT OR IGNORE INTO seen(value, occurrences) VALUES (?, 1)",
                            (row_hash,),
                        )
                        if cursor.rowcount == 1:
                            writer.writerow(values)
                            output_rows += 1
                            output_positives += int(is_positive)
                        else:
                            connection.execute(
                                "UPDATE seen SET occurrences = occurrences + 1 WHERE value = ?",
                                (row_hash,),
                            )
                    output_handle.flush()
                    os.fsync(output_handle.fileno())
                connection.commit()
                duplicate_counts = cast(
                    tuple[int, int],
                    connection.execute(
                        "SELECT COUNT(*), COALESCE(MAX(occurrences), 1) "
                        "FROM seen WHERE occurrences > 1"
                    ).fetchone(),
                )
                duplicate_group_count, max_duplicate_group_size = duplicate_counts
            finally:
                connection.close()

        if source_rows == output_rows:
            raise DerivationError("source contains no exact duplicate rows to derive")
        output_sha256 = _file_hash(temporary_output)
        output_size = temporary_output.stat().st_size
        manifest: dict[str, object] = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "transformation_version": TRANSFORMATION_VERSION,
            "dataset_id": request["dataset_id"],
            "source_dataset_version": request["source_dataset_version"],
            "derived_dataset_version": request["derived_dataset_version"],
            "created_at": request["created_at"],
            "source_sha256": source_sha256,
            "source_size_bytes": source_size,
            "output_sha256": output_sha256,
            "output_size_bytes": output_size,
            "header_sha256": _canonical_hash(required),
            "source_row_count": source_rows,
            "output_row_count": output_rows,
            "removed_duplicate_row_count": source_rows - output_rows,
            "duplicate_group_count": duplicate_group_count,
            "max_duplicate_group_size": max_duplicate_group_size,
            "source_positive_count": source_positives,
            "output_positive_count": output_positives,
            "removed_positive_count": source_positives - output_positives,
            "preserved_row_policy": "first_occurrence_in_source_order",
            "source_bytes_modified": False,
            "output_bytes_committed": False,
            "network_acquisition_executed": False,
            "splits_created": False,
            "training_executed": False,
            "promotable_for_training": False,
        }
        _validate_manifest(manifest)
        os.replace(temporary_output, output)
        _write_json_atomic(manifest_path, manifest)
        return DeduplicationOutputs(output, manifest_path, manifest)
    finally:
        temporary_output.unlink(missing_ok=True)
