from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from momo_fdvs_ml.manifest import load_manifest, validate_manifest
from momo_fdvs_ml.synthetic import (
    CONTROLLED_OPERATION_SETS,
    DEFAULT_SEED,
    apply_controlled_operations,
    assign_group_splits,
    generate_controlled_dataset,
    render_generic_receipt,
    verify_recorded_report,
)


def test_group_split_is_deterministic_and_complete() -> None:
    groups = [f"group-{index}" for index in range(6)]

    first = assign_group_splits(groups, seed=42)
    second = assign_group_splits(list(reversed(groups)), seed=42)

    assert first == second
    assert set(first) == set(groups)
    assert set(first.values()) == {"train", "validation", "test"}


@pytest.mark.parametrize("count", [0, 1, 2])
def test_group_split_requires_three_groups(count: int) -> None:
    with pytest.raises(ValueError, match="at least three"):
        assign_group_splits([f"group-{index}" for index in range(count)], seed=42)


def test_controlled_generation_is_byte_reproducible(tmp_path: Path) -> None:
    first = generate_controlled_dataset(tmp_path / "first", seed=DEFAULT_SEED)
    second = generate_controlled_dataset(tmp_path / "second", seed=DEFAULT_SEED)

    assert first.validation.is_valid
    assert first.manifest.manifest_hash == second.manifest.manifest_hash
    assert first.manifest.split_hash == second.manifest.split_hash
    first_hashes = {record.sample_id: record.sha256 for record in first.manifest.records}
    second_hashes = {record.sample_id: record.sha256 for record in second.manifest.records}
    assert first_hashes == second_hashes
    assert verify_recorded_report(first.root, first.manifest) == ()


def test_controlled_generation_covers_declared_operations_and_keeps_groups_together(
    tmp_path: Path,
) -> None:
    generated = generate_controlled_dataset(tmp_path / "dataset", seed=DEFAULT_SEED)
    manifest = generated.manifest
    expected_operations = {operation for group in CONTROLLED_OPERATION_SETS for operation in group}
    actual_operations = {
        operation for record in manifest.records for operation in record.tamper_operations
    }
    group_splits: dict[str, set[str]] = {}
    parent_by_id = {record.sample_id: record for record in manifest.records}

    for record in manifest.records:
        group_splits.setdefault(record.source_group_id, set()).add(record.split)
        image_path = generated.root / record.relative_path
        with Image.open(image_path) as image:
            assert image.size == (640, 900)
        if record.parent_sample_id:
            parent = parent_by_id[record.parent_sample_id]
            assert parent.source_group_id == record.source_group_id
            assert parent.split == record.split
            metadata = json.loads(record.tamper_metadata)
            assert {item["name"] for item in metadata["operations"]} == set(
                record.tamper_operations
            )
            assert all(len(item["box"]) == 4 for item in metadata["operations"])

    assert actual_operations == expected_operations
    assert all(len(splits) == 1 for splits in group_splits.values())
    assert generated.validation.label_counts == {"genuine": 6, "fraudulent": 6}
    assert generated.validation.source_type_counts == {
        "synthetic": 6,
        "controlled_tamper": 6,
    }


def test_generic_receipt_contains_no_protected_brand_or_personal_data() -> None:
    image = render_generic_receipt(group_number=1, seed=DEFAULT_SEED)
    assert image.mode == "RGB"
    assert image.size == (640, 900)


def test_unknown_operation_is_rejected() -> None:
    source = render_generic_receipt(group_number=1, seed=DEFAULT_SEED)
    with pytest.raises(ValueError, match="unsupported controlled operation"):
        apply_controlled_operations(source, ["unknown_edit"])


def test_generation_requires_three_groups(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least three"):
        generate_controlled_dataset(tmp_path / "dataset", group_count=2)


def test_recorded_report_detects_drift(tmp_path: Path) -> None:
    generated = generate_controlled_dataset(tmp_path / "dataset")
    report_path = generated.root / "dataset_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["split_hash"] = "0" * 64
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    errors = verify_recorded_report(generated.root, generated.manifest)

    assert errors == ("recorded split_hash does not match manifest",)


def test_recorded_report_handles_missing_file(tmp_path: Path) -> None:
    generated = generate_controlled_dataset(tmp_path / "dataset")
    (generated.root / "dataset_report.json").unlink()
    assert verify_recorded_report(generated.root, generated.manifest)[0].startswith(
        "unable to read"
    )


def test_committed_controlled_dataset_is_current() -> None:
    root = Path(__file__).resolve().parents[1] / "data" / "controlled"
    manifest = load_manifest(root / "manifest.csv")
    validation = validate_manifest(manifest, root=root)

    assert validation.is_valid
    assert verify_recorded_report(root, manifest) == ()


def test_colab_preflight_is_valid_and_contains_no_training_code() -> None:
    notebook_path = (
        Path(__file__).resolve().parents[1] / "notebooks" / "P10_COLAB_DATA_PREFLIGHT.ipynb"
    )
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

    assert notebook["nbformat"] == 4
    assert "REPLACE_WITH_P10_MERGE_SHA" in source
    assert "python scripts/verify.py --ml" in source
    assert ".fit(" not in source
    assert "model.save" not in source
