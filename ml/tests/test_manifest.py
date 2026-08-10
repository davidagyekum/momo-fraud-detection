from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path

import pytest

from momo_fdvs_ml.manifest import (
    MANIFEST_COLUMNS,
    ManifestError,
    load_manifest,
    scan_text_for_private_identifiers,
    validate_manifest,
    write_manifest,
)
from momo_fdvs_ml.synthetic import generate_controlled_dataset


def _generated(tmp_path: Path):  # type: ignore[no-untyped-def]
    return generate_controlled_dataset(tmp_path / "dataset")


def _codes(report):  # type: ignore[no-untyped-def]
    return {issue.code for issue in report.errors}


def test_loader_rejects_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "manifest.csv"
    path.write_text("sample_id,relative_path\none,image.png\n", encoding="utf-8")

    with pytest.raises(ManifestError, match="missing columns"):
        load_manifest(path)


def test_repository_sample_manifest_matches_loader_schema() -> None:
    path = Path(__file__).resolve().parents[2] / "samples" / "receipt_dataset_manifest.csv"
    manifest = load_manifest(path)

    assert len(manifest.records) == 6
    assert manifest.records[1].tamper_operations == (
        "amount_replace",
        "text_misalignment",
    )


def test_loader_rejects_empty_manifest(tmp_path: Path) -> None:
    path = tmp_path / "manifest.csv"
    path.write_text(",".join(MANIFEST_COLUMNS) + "\n", encoding="utf-8")
    with pytest.raises(ManifestError, match="at least one"):
        load_manifest(path)


@pytest.mark.parametrize("value", ["yes", "1", "unknown"])
def test_loader_rejects_invalid_boolean(tmp_path: Path, value: str) -> None:
    generated = _generated(tmp_path)
    rows = list(csv.DictReader(generated.manifest.path.read_text(encoding="utf-8").splitlines()))
    rows[0]["contains_personal_data"] = value
    with generated.manifest.path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ManifestError, match="true or false"):
        load_manifest(generated.manifest.path)


def test_loader_rejects_invalid_seed(tmp_path: Path) -> None:
    generated = _generated(tmp_path)
    rows = list(csv.DictReader(generated.manifest.path.read_text(encoding="utf-8").splitlines()))
    rows[0]["generated_seed"] = "not-an-integer"
    with generated.manifest.path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ManifestError, match="must be an integer"):
        load_manifest(generated.manifest.path)


def test_missing_and_corrupt_images_are_rejected(tmp_path: Path) -> None:
    generated = _generated(tmp_path)
    first, second, *remaining = generated.manifest.records
    (generated.root / first.relative_path).unlink()
    (generated.root / second.relative_path).write_text("not an image", encoding="utf-8")
    records = (
        first,
        replace(second, sha256="4c6b7097cb8d2c0a86caed5af8af1f159fcb251bb079cddb3c2b4a8f0c4f928a"),
        *remaining,
    )
    manifest = write_manifest(generated.root / "modified.csv", records)

    codes = _codes(validate_manifest(manifest, root=generated.root))

    assert "missing_file" in codes
    assert {"hash_mismatch", "corrupt_image"} <= codes


def test_duplicate_hash_and_conflicting_label_are_rejected(tmp_path: Path) -> None:
    generated = _generated(tmp_path)
    first, second, *remaining = generated.manifest.records
    copied = replace(
        second,
        relative_path=first.relative_path,
        sha256=first.sha256,
        label="fraudulent" if first.label != "fraudulent" else "genuine",
    )
    manifest = write_manifest(generated.root / "duplicate.csv", (first, copied, *remaining))

    codes = _codes(validate_manifest(manifest, root=generated.root))

    assert "conflicting_duplicate_labels" in codes


def test_group_and_parent_leakage_are_rejected(tmp_path: Path) -> None:
    generated = _generated(tmp_path)
    records = list(generated.manifest.records)
    child_index = next(index for index, record in enumerate(records) if record.parent_sample_id)
    child = records[child_index]
    records[child_index] = replace(child, split="test" if child.split != "test" else "train")
    manifest = write_manifest(generated.root / "leak.csv", records)

    codes = _codes(validate_manifest(manifest, root=generated.root))

    assert {"source_group_leakage", "parent_group_leakage"} <= codes


def test_unsafe_path_and_invalid_location_are_rejected(tmp_path: Path) -> None:
    generated = _generated(tmp_path)
    first, *remaining = generated.manifest.records
    unsafe = replace(first, relative_path="../private/receipt.png")
    both = replace(remaining[0], private_object_id="private-id")
    manifest = write_manifest(generated.root / "paths.csv", (unsafe, both, *remaining[1:]))

    codes = _codes(validate_manifest(manifest, root=generated.root))

    assert {"unsafe_path", "invalid_location"} <= codes


def test_private_identifier_scanner_flags_phone_email_reference_and_name() -> None:
    text = (
        "phone 0241234567 email person@example.org reference: TXN12345678 recipient: KWAME MENSAH"
    )
    assert set(scan_text_for_private_identifiers(text)) == {
        "phone_number",
        "email_address",
        "transaction_reference",
        "personal_name",
    }
    assert scan_text_for_private_identifiers("reference: DEMO-0001 recipient: DEMO RECIPIENT") == ()


def test_manifest_rejects_unapproved_private_identifier(tmp_path: Path) -> None:
    generated = _generated(tmp_path)
    first, *remaining = generated.manifest.records
    private = replace(first, notes="recipient: KWAME MENSAH, phone 0241234567")
    manifest = write_manifest(generated.root / "private.csv", (private, *remaining))
    assert "unapproved_private_identifier" in _codes(
        validate_manifest(manifest, root=generated.root)
    )


def test_augmentation_is_training_only(tmp_path: Path) -> None:
    generated = _generated(tmp_path)
    records = list(generated.manifest.records)
    index = next(
        index
        for index, record in enumerate(records)
        if record.parent_sample_id and record.split != "train"
    )
    record = records[index]
    operations = (*record.tamper_operations, "augment:brightness")
    metadata = json.loads(record.tamper_metadata)
    metadata["operations"].append({"name": "augment:brightness", "box": [0, 0, 640, 900]})
    records[index] = replace(
        record,
        tamper_operations=operations,
        tamper_metadata=json.dumps(metadata, sort_keys=True, separators=(",", ":")),
    )
    manifest = write_manifest(generated.root / "augmentation.csv", records)
    assert "augmentation_outside_train" in _codes(validate_manifest(manifest, root=generated.root))


def test_tamper_metadata_must_match_operations(tmp_path: Path) -> None:
    generated = _generated(tmp_path)
    records = list(generated.manifest.records)
    index = next(index for index, record in enumerate(records) if record.parent_sample_id)
    records[index] = replace(records[index], tamper_metadata='{"operations":[]}')
    manifest = write_manifest(generated.root / "metadata.csv", records)
    assert "tamper_metadata_mismatch" in _codes(validate_manifest(manifest, root=generated.root))


def test_real_data_requires_private_location_permission_and_anonymisation(
    tmp_path: Path,
) -> None:
    generated = _generated(tmp_path)
    first, *remaining = generated.manifest.records
    real = replace(
        first,
        source_type="real_authorised",
        consent_or_licence_reference="",
        contains_personal_data=True,
        anonymisation_status="not_applicable",
        generated_seed=None,
    )
    manifest = write_manifest(generated.root / "real.csv", (real, *remaining))
    codes = _codes(validate_manifest(manifest, root=generated.root))
    assert {
        "missing_permission",
        "real_data_not_anonymised",
        "real_data_in_repository_path",
    } <= codes


def test_validation_report_raise_for_errors(tmp_path: Path) -> None:
    generated = _generated(tmp_path)
    first, *remaining = generated.manifest.records
    manifest = write_manifest(
        generated.root / "bad.csv", (replace(first, label="unknown"), *remaining)
    )
    report = validate_manifest(manifest, root=generated.root)
    with pytest.raises(ManifestError, match="invalid_label"):
        report.raise_for_errors()
    assert report.as_dict()["error_count"] >= 1
