"""Executable dataset registry, portable-fixture and withdrawal governance."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Final

GOVERNANCE_VERSION: Final = "data-governance-v1"
REGISTRY_VERSION: Final = "dataset-registry-v1"
EXPECTED_DATASET_IDS: Final = {
    "paysim",
    "momtsim-v1",
    "momtsim-v2",
    "stfd",
    "fsts",
    "ghana-private",
}
SCHEMA_REQUIRED_FIELDS: Final[dict[str, frozenset[str]]] = {
    "transaction": frozenset(
        {
            "step",
            "transaction_type",
            "amount",
            "initiator_id",
            "recipient_id",
            "old_balance_initiator",
            "new_balance_initiator",
            "old_balance_recipient",
            "new_balance_recipient",
            "label_is_fraud",
            "dataset_source",
            "source_row_id",
        }
    ),
    "screenshot": frozenset(
        {
            "image_id",
            "source_group_id",
            "parent_image_id",
            "provenance",
            "participant_id_hash",
            "provider_family",
            "template_family",
            "template_version",
            "capture_channel",
            "device_family",
            "os_family",
            "resolution",
            "theme",
            "image_class",
            "tamper_target",
            "tamper_method",
            "benign_transform",
            "mask_path",
            "transcript_path",
            "ground_truth_fields_path",
            "split",
            "consent_scope",
            "permission_reference",
            "sha256",
        }
    ),
    "ocr-truth": frozenset(
        {
            "image_id",
            "amount",
            "recipient_name",
            "recipient_wallet",
            "reference",
            "timestamp",
            "status",
            "full_transcript",
        }
    ),
    "edit-manifest": frozenset(
        {"edit_id", "source_image_id", "derived_image_id", "seed", "operations"}
    ),
    "split-manifest": frozenset(
        {"schema_version", "dataset_id", "seed", "frozen", "manifest_sha256", "groups"}
    ),
    "run-manifest": frozenset(
        {
            "schema_version",
            "run_id",
            "profile",
            "git_commit",
            "repo_dirty",
            "python_version",
            "dependency_lock_sha256",
            "dataset_manifest_sha256",
            "split_manifest_sha256",
            "seed",
            "started_at",
            "completed_at",
            "status",
            "checkpoint_sha256s",
        }
    ),
}
FIXTURE_TO_SCHEMA: Final = {
    "transaction.fixture.json": "transaction",
    "screenshot.fixture.json": "screenshot",
    "ocr-truth.fixture.json": "ocr-truth",
    "edit-manifest.fixture.json": "edit-manifest",
    "split-manifest.fixture.json": "split-manifest",
    "run-manifest.fixture.json": "run-manifest",
}
SHA256_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")
SHA1_PATTERN: Final = re.compile(r"^[0-9a-f]{40}$")
CANONICAL_IMAGE_LABELS: Final = {"unaltered", "tampered"}
CONSENT_SCOPES: Final = {"internal_only", "release_approved", "synthetic_not_applicable"}


class GovernanceError(ValueError):
    """Raised when data governance is incomplete, unsafe or internally inconsistent."""


def _load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GovernanceError(f"unable to load governed document {path.as_posix()}") from exc
    if not isinstance(value, dict):
        raise GovernanceError(f"governed document {path.name} must contain an object")
    return value


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _expect_exact_keys(payload: Mapping[str, object], expected: frozenset[str], name: str) -> None:
    supplied = set(payload)
    missing = sorted(expected - supplied)
    extra = sorted(supplied - expected)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if extra:
            details.append(f"unknown {', '.join(extra)}")
        raise GovernanceError(f"{name} fields invalid: {'; '.join(details)}")


def _expect_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernanceError(f"{name} must be a non-empty string")
    return value


def _expect_number(value: object, name: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GovernanceError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or (minimum is not None and result < minimum):
        raise GovernanceError(f"{name} is outside the allowed range")
    return result


def _expect_sha256(value: object, name: str) -> str:
    text = _expect_string(value, name)
    if SHA256_PATTERN.fullmatch(text) is None:
        raise GovernanceError(f"{name} must be a lowercase SHA-256")
    return text


def _expect_iso_datetime(value: object, name: str, *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    text = _expect_string(value, name)
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GovernanceError(f"{name} must be an ISO-8601 datetime") from exc


def load_and_validate_registry(data_root: Path) -> dict[str, object]:
    """Load JSON-compatible YAML and fail closed for incomplete source governance."""

    registry = _load_json(data_root / "registry.yaml")
    if registry.get("registry_version") != REGISTRY_VERSION:
        raise GovernanceError("unsupported dataset registry version")
    datasets = registry.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        raise GovernanceError("dataset registry must contain entries")
    ids: set[str] = set()
    required = {
        "dataset_id",
        "display_name",
        "category",
        "source_locator",
        "version",
        "required",
        "enabled",
        "acquisition_status",
        "permission_status",
        "licence_status",
        "redistribution",
        "data_classification",
        "card_path",
        "expected_schema",
        "allowed_purposes",
        "prohibited_uses",
    }
    for raw_entry in datasets:
        if not isinstance(raw_entry, dict):
            raise GovernanceError("dataset registry entries must be objects")
        _expect_exact_keys(raw_entry, frozenset(required), "registry entry")
        dataset_id = _expect_string(raw_entry["dataset_id"], "dataset_id")
        if dataset_id in ids:
            raise GovernanceError("dataset registry IDs must be unique")
        ids.add(dataset_id)
        for field in (
            "display_name",
            "category",
            "source_locator",
            "version",
            "permission_status",
            "licence_status",
            "redistribution",
            "data_classification",
        ):
            _expect_string(raw_entry[field], field)
        if not isinstance(raw_entry["required"], bool) or not isinstance(
            raw_entry["enabled"], bool
        ):
            raise GovernanceError("registry required/enabled flags must be booleans")
        if raw_entry["acquisition_status"] not in {
            "not_acquired",
            "quarantined",
            "registered",
        }:
            raise GovernanceError("invalid acquisition status")
        purposes = raw_entry["allowed_purposes"]
        prohibited = raw_entry["prohibited_uses"]
        if (
            not isinstance(purposes, list)
            or not purposes
            or not all(isinstance(item, str) and item for item in purposes)
        ):
            raise GovernanceError("allowed purposes must be a non-empty string list")
        if (
            not isinstance(prohibited, list)
            or not prohibited
            or not all(isinstance(item, str) and item for item in prohibited)
        ):
            raise GovernanceError("prohibited uses must be a non-empty string list")
        approved = (
            raw_entry["permission_status"] == "approved"
            and raw_entry["licence_status"] in {"verified", "not_applicable_private_consent"}
            and raw_entry["acquisition_status"] == "registered"
        )
        if raw_entry["enabled"] and not approved:
            raise GovernanceError(f"{dataset_id} cannot be enabled before approval/registration")
        card = data_root.parent / _expect_string(raw_entry["card_path"], "card_path")
        schema = data_root.parent / _expect_string(raw_entry["expected_schema"], "expected_schema")
        if not card.is_file() or not schema.is_file():
            raise GovernanceError(f"{dataset_id} card/schema path does not exist")
        card_text = card.read_text(encoding="utf-8")
        for heading in (
            "Licence/permission",
            "Redistribution",
            "Class distribution",
            "Limitations",
        ):
            if heading not in card_text:
                raise GovernanceError(f"{dataset_id} card is missing {heading}")
    if ids != EXPECTED_DATASET_IDS:
        raise GovernanceError("dataset registry does not contain the exact canonical source IDs")
    fsts = next(entry for entry in datasets if entry["dataset_id"] == "fsts")
    if fsts["required"] or fsts["enabled"]:
        raise GovernanceError("FSTS must remain optional and disabled by default")
    ghana = next(entry for entry in datasets if entry["dataset_id"] == "ghana-private")
    if (
        ghana["permission_status"] != "consent_required"
        or ghana["redistribution"] != "internal_only"
    ):
        raise GovernanceError("Ghana-private must require consent and default to internal-only")
    return registry


def validate_schema_documents(data_root: Path) -> dict[str, str]:
    """Validate portable schema identity, strictness and required-field alignment."""

    hashes: dict[str, str] = {}
    for schema_name, required_fields in SCHEMA_REQUIRED_FIELDS.items():
        schema = _load_json(data_root / "schemas" / f"{schema_name}.schema.json")
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise GovernanceError(f"{schema_name} must use JSON Schema 2020-12")
        if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
            raise GovernanceError(f"{schema_name} must be a strict object schema")
        required = schema.get("required")
        if not isinstance(required, list) or set(required) != required_fields:
            raise GovernanceError(f"{schema_name} required fields drifted")
        properties = schema.get("properties")
        if not isinstance(properties, dict) or set(properties) != required_fields:
            raise GovernanceError(f"{schema_name} properties drifted")
        hashes[schema_name] = _canonical_hash(schema)
    return hashes


def _validate_transaction(payload: Mapping[str, object]) -> None:
    _expect_exact_keys(payload, SCHEMA_REQUIRED_FIELDS["transaction"], "transaction")
    if isinstance(payload["step"], bool) or not isinstance(payload["step"], int):
        raise GovernanceError("transaction step must be an integer")
    _expect_number(payload["amount"], "transaction amount", minimum=0)
    for field in ("initiator_id", "recipient_id"):
        if not _expect_string(payload[field], field).startswith("ENTITY_"):
            raise GovernanceError(f"{field} must be a pseudonymous ENTITY identifier")
    for field in (
        "old_balance_initiator",
        "new_balance_initiator",
        "old_balance_recipient",
        "new_balance_recipient",
    ):
        if payload[field] is not None:
            _expect_number(payload[field], field)
    if payload["label_is_fraud"] not in {0, 1} or isinstance(payload["label_is_fraud"], bool):
        raise GovernanceError("label_is_fraud must be 0 or 1")
    if payload["dataset_source"] not in {
        "paysim",
        "momtsim_v1",
        "momtsim_v2",
        "controlled_synthetic",
    }:
        raise GovernanceError("transaction dataset source is not registered")
    _expect_string(payload["transaction_type"], "transaction_type")
    _expect_string(payload["source_row_id"], "source_row_id")


def _validate_screenshot(payload: Mapping[str, object]) -> None:
    _expect_exact_keys(payload, SCHEMA_REQUIRED_FIELDS["screenshot"], "screenshot")
    image_id = _expect_string(payload["image_id"], "image_id")
    if not image_id.startswith("FIXTURE_"):
        raise GovernanceError("committed screenshot fixtures must use FIXTURE IDs")
    if payload["image_class"] not in CANONICAL_IMAGE_LABELS:
        raise GovernanceError("image_class must be unaltered or tampered")
    if payload["consent_scope"] not in CONSENT_SCOPES:
        raise GovernanceError("consent_scope is required and must be canonical")
    for field in (
        "source_group_id",
        "provider_family",
        "template_family",
        "template_version",
        "device_family",
        "transcript_path",
        "ground_truth_fields_path",
    ):
        _expect_string(payload[field], field)
    if payload["provenance"] not in {"controlled_real", "synthetic_template", "stfd", "fsts"}:
        raise GovernanceError("screenshot provenance is invalid")
    if payload["capture_channel"] not in {"sms", "notification", "app_receipt", "history", "other"}:
        raise GovernanceError("capture_channel is invalid")
    if payload["os_family"] not in {"android", "ios", "other"}:
        raise GovernanceError("os_family is invalid")
    if payload["theme"] not in {"light", "dark", "unknown"}:
        raise GovernanceError("theme is invalid")
    if payload["split"] not in {"train", "validation", "test"}:
        raise GovernanceError("screenshot split is invalid")
    targets = {"none", "amount", "recipient", "reference", "datetime", "status", "header", "multi"}
    methods = {
        "none",
        "replacement",
        "splicing",
        "removal_insertion",
        "copy_move",
        "inpainting",
        "composite",
    }
    transforms = {"none", "jpeg", "webp", "resize", "crop", "blur", "screen_photo", "other"}
    if payload["tamper_target"] not in targets or payload["tamper_method"] not in methods:
        raise GovernanceError("tamper target/method is invalid")
    if payload["benign_transform"] not in transforms:
        raise GovernanceError("benign transform is invalid")
    if payload["image_class"] == "unaltered" and (
        payload["tamper_target"] != "none" or payload["tamper_method"] != "none"
    ):
        raise GovernanceError("unaltered screenshots cannot declare tamper operations")
    if payload["image_class"] == "tampered" and (
        payload["tamper_target"] == "none" or payload["tamper_method"] == "none"
    ):
        raise GovernanceError("tampered screenshots require a target and method")
    _expect_string(payload["permission_reference"], "permission_reference")
    _expect_sha256(payload["sha256"], "screenshot sha256")
    resolution = payload["resolution"]
    if (
        not isinstance(resolution, list)
        or len(resolution) != 2
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 1 for item in resolution
        )
    ):
        raise GovernanceError("resolution must contain two positive integers")
    provenance = payload["provenance"]
    participant_hash = payload["participant_id_hash"]
    if provenance == "controlled_real":
        _expect_sha256(participant_hash, "participant_id_hash")
        if payload["consent_scope"] not in {"internal_only", "release_approved"}:
            raise GovernanceError("controlled-real screenshots require recorded consent scope")
    elif provenance == "synthetic_template":
        if participant_hash is not None or payload["consent_scope"] != "synthetic_not_applicable":
            raise GovernanceError("synthetic screenshots cannot carry participant consent/linkage")
    elif provenance in {"stfd", "fsts"}:
        if participant_hash is not None or payload["consent_scope"] == "synthetic_not_applicable":
            raise GovernanceError(
                "external screenshots require licence scope without participant linkage"
            )


def _validate_ocr_truth(payload: Mapping[str, object]) -> None:
    _expect_exact_keys(payload, SCHEMA_REQUIRED_FIELDS["ocr-truth"], "ocr truth")
    for field_name in (
        "amount",
        "recipient_name",
        "recipient_wallet",
        "reference",
        "timestamp",
        "status",
    ):
        field = payload[field_name]
        if not isinstance(field, dict):
            raise GovernanceError(f"OCR {field_name} must be an object")
        _expect_exact_keys(field, frozenset({"raw", "normalized", "bbox"}), f"OCR {field_name}")
        bbox = field["bbox"]
        if (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in bbox)
        ):
            raise GovernanceError(f"OCR {field_name} bbox is invalid")
    transcript = _expect_string(payload["full_transcript"], "full_transcript")
    if "SYNTHETIC" not in transcript and "DEMO" not in transcript:
        raise GovernanceError("committed OCR truth must be demonstrably fictitious")


def _validate_edit_manifest(payload: Mapping[str, object]) -> None:
    _expect_exact_keys(payload, SCHEMA_REQUIRED_FIELDS["edit-manifest"], "edit manifest")
    operations = payload["operations"]
    if not isinstance(operations, list) or not operations:
        raise GovernanceError("edit manifest requires operations")
    for operation in operations:
        if not isinstance(operation, dict):
            raise GovernanceError("edit operations must be objects")
        _expect_exact_keys(
            operation,
            frozenset({"target", "method", "bbox", "old_value", "new_value"}),
            "edit operation",
        )
        if operation["target"] == "none" or operation["method"] == "none":
            raise GovernanceError("controlled edits require a real target and method")
        bbox = operation["bbox"]
        if (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in bbox)
        ):
            raise GovernanceError("edit operation bbox is invalid")
        _expect_string(operation["old_value"], "old_value")
        _expect_string(operation["new_value"], "new_value")
    if isinstance(payload["seed"], bool) or not isinstance(payload["seed"], int):
        raise GovernanceError("edit seed must be an integer")


def _validate_split_manifest(payload: Mapping[str, object]) -> None:
    _expect_exact_keys(payload, SCHEMA_REQUIRED_FIELDS["split-manifest"], "split manifest")
    if payload["schema_version"] != "split-manifest-v1" or payload["frozen"] is not True:
        raise GovernanceError("split manifest must be versioned and frozen")
    _expect_sha256(payload["manifest_sha256"], "manifest_sha256")
    groups = payload["groups"]
    if not isinstance(groups, dict):
        raise GovernanceError("split groups must be an object")
    _expect_exact_keys(groups, frozenset({"train", "validation", "test"}), "split groups")
    seen: set[str] = set()
    for split in ("train", "validation", "test"):
        values = groups[split]
        if (
            not isinstance(values, list)
            or not values
            or not all(isinstance(item, str) and item for item in values)
        ):
            raise GovernanceError(f"{split} groups must be a non-empty string list")
        if len(values) != len(set(values)) or seen.intersection(values):
            raise GovernanceError("split source groups must be unique and disjoint")
        seen.update(values)


def _validate_run_manifest(payload: Mapping[str, object]) -> None:
    _expect_exact_keys(payload, SCHEMA_REQUIRED_FIELDS["run-manifest"], "run manifest")
    if payload["schema_version"] != "run-manifest-v1":
        raise GovernanceError("unsupported run manifest version")
    if payload["profile"] not in {"unit", "smoke", "full"}:
        raise GovernanceError("run profile is invalid")
    if payload["status"] not in {"created", "running", "completed", "failed", "cancelled"}:
        raise GovernanceError("run status is invalid")
    if payload["repo_dirty"] is not False:
        raise GovernanceError("reportable run manifests require a clean repository")
    if SHA1_PATTERN.fullmatch(_expect_string(payload["git_commit"], "git_commit")) is None:
        raise GovernanceError("git_commit must contain 40 lowercase hexadecimal characters")
    for field in (
        "dependency_lock_sha256",
        "dataset_manifest_sha256",
        "split_manifest_sha256",
    ):
        _expect_sha256(payload[field], field)
    if not _expect_string(payload["python_version"], "python_version").startswith("3.12."):
        raise GovernanceError("run manifest must use the supported Python 3.12 runtime")
    if isinstance(payload["seed"], bool) or not isinstance(payload["seed"], int):
        raise GovernanceError("run seed must be an integer")
    _expect_iso_datetime(payload["started_at"], "started_at")
    _expect_iso_datetime(payload["completed_at"], "completed_at", nullable=True)
    checkpoints = payload["checkpoint_sha256s"]
    if not isinstance(checkpoints, list) or len(checkpoints) != len(set(checkpoints)):
        raise GovernanceError("checkpoint hashes must be a unique list")
    for checkpoint in checkpoints:
        _expect_sha256(checkpoint, "checkpoint sha256")


def validate_fixture_payload(schema_name: str, payload: Mapping[str, object]) -> None:
    """Validate one fixture against the executable counterpart to its portable schema."""

    validators = {
        "transaction": _validate_transaction,
        "screenshot": _validate_screenshot,
        "ocr-truth": _validate_ocr_truth,
        "edit-manifest": _validate_edit_manifest,
        "split-manifest": _validate_split_manifest,
        "run-manifest": _validate_run_manifest,
    }
    try:
        validator = validators[schema_name]
    except KeyError as exc:
        raise GovernanceError("unknown portable schema") from exc
    validator(payload)


def _validate_public_fixture_markers(schema_name: str, payload: Mapping[str, object]) -> None:
    """Prove committed examples are fictitious rather than merely schema-conforming."""

    canonical_text = json.dumps(payload, sort_keys=True, ensure_ascii=True).upper()
    if not any(marker in canonical_text for marker in ("SYNTHETIC", "DEMO", "FIXTURE")):
        raise GovernanceError(f"{schema_name} public fixture lacks a fictitious marker")
    if schema_name == "transaction" and payload.get("dataset_source") != "controlled_synthetic":
        raise GovernanceError("committed transaction fixture must be controlled synthetic")
    if schema_name == "screenshot" and (
        payload.get("provenance") != "synthetic_template"
        or payload.get("consent_scope") != "synthetic_not_applicable"
    ):
        raise GovernanceError("committed screenshot fixture must be synthetic and participant-free")


def load_withdrawal_ledger(path: Path) -> frozenset[str]:
    """Validate a private/synthetic ledger shape and return blocked participant hashes."""

    ledger = _load_json(path)
    if ledger.get("schema_version") != "withdrawal-ledger-v1":
        raise GovernanceError("unsupported withdrawal ledger version")
    entries = ledger.get("entries")
    if not isinstance(entries, list):
        raise GovernanceError("withdrawal ledger entries must be a list")
    blocked: set[str] = set()
    required = frozenset(
        {"participant_id_hash", "withdrawn_at", "scope", "status", "request_reference"}
    )
    for entry in entries:
        if not isinstance(entry, dict):
            raise GovernanceError("withdrawal ledger entries must be objects")
        _expect_exact_keys(entry, required, "withdrawal entry")
        participant_hash = _expect_sha256(entry["participant_id_hash"], "participant_id_hash")
        _expect_iso_datetime(entry["withdrawn_at"], "withdrawn_at")
        if entry["scope"] not in {
            "all_research_data_and_derivatives",
            "future_processing_only",
            "public_release_only",
        }:
            raise GovernanceError("withdrawal scope is invalid")
        if entry["status"] not in {
            "pending_disable",
            "pending_deletion",
            "pending_rebuild",
            "completed",
        }:
            raise GovernanceError("withdrawal status is invalid")
        _expect_string(entry["request_reference"], "request_reference")
        if participant_hash in blocked:
            raise GovernanceError("withdrawal participant hashes must be unique")
        blocked.add(participant_hash)
    return frozenset(blocked)


def assert_participant_not_withdrawn(participant_id_hash: str, blocked: frozenset[str]) -> None:
    """Fail before including a withdrawn participant in a manifest or processing run."""

    _expect_sha256(participant_id_hash, "participant_id_hash")
    if participant_id_hash in blocked:
        raise GovernanceError("participant is present in the withdrawal ledger")


def validate_taxonomy(data_root: Path) -> int:
    taxonomy = _load_json(data_root / "tamper-taxonomy.json")
    if taxonomy.get("taxonomy_version") != "tamper-taxonomy-v1":
        raise GovernanceError("unsupported tamper taxonomy version")
    distribution = taxonomy.get("planned_tampered_target_distribution_percent")
    if not isinstance(distribution, dict) or set(distribution) != {
        "amount",
        "recipient",
        "reference",
        "datetime",
        "status",
        "header",
        "multi",
    }:
        raise GovernanceError("tamper target distribution is incomplete")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in distribution.values()
    ):
        raise GovernanceError("taxonomy percentages must be non-negative integers")
    total = sum(distribution.values())
    if total != 100 or taxonomy.get("total_percent") != 100:
        raise GovernanceError("taxonomy percentages must sum to 100")
    return total


def governance_report(data_root: Path) -> dict[str, object]:
    """Validate every tracked governance artifact without acquiring or training on data."""

    registry = load_and_validate_registry(data_root)
    schema_hashes = validate_schema_documents(data_root)
    fixture_hashes: dict[str, str] = {}
    for filename, schema_name in FIXTURE_TO_SCHEMA.items():
        fixture = _load_json(data_root / "fixtures" / filename)
        validate_fixture_payload(schema_name, fixture)
        _validate_public_fixture_markers(schema_name, fixture)
        fixture_hashes[filename] = _canonical_hash(fixture)
    withdrawal_fixture = _load_json(data_root / "fixtures" / "withdrawal-ledger.fixture.json")
    blocked = load_withdrawal_ledger(data_root / "fixtures" / "withdrawal-ledger.fixture.json")
    taxonomy_total = validate_taxonomy(data_root)
    taxonomy = _load_json(data_root / "tamper-taxonomy.json")
    datasets = registry["datasets"]
    if not isinstance(datasets, list):
        raise GovernanceError("validated registry unexpectedly changed type")
    return {
        "governance_version": GOVERNANCE_VERSION,
        "registry_version": REGISTRY_VERSION,
        "registry_hash": _canonical_hash(registry),
        "registry_entry_count": len(datasets),
        "enabled_dataset_count": sum(
            1 for entry in datasets if isinstance(entry, dict) and entry.get("enabled") is True
        ),
        "schema_count": len(schema_hashes),
        "schema_hashes": dict(sorted(schema_hashes.items())),
        "fixture_count": len(FIXTURE_TO_SCHEMA),
        "fixture_hashes": dict(sorted(fixture_hashes.items())),
        "withdrawal_fixture_entry_count": len(blocked),
        "withdrawal_fixture_hash": _canonical_hash(withdrawal_fixture),
        "taxonomy_total_percent": taxonomy_total,
        "taxonomy_hash": _canonical_hash(taxonomy),
        "acquisition_executed": False,
        "training_executed": False,
    }
