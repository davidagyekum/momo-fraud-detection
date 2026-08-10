from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

import pytest

from momo_fdvs_ml.feature_schema import FEATURE_NAMES, RISK_CLASSES
from momo_fdvs_ml.manifest import load_manifest
from momo_fdvs_ml.structured_dataset import (
    STRUCTURED_COLUMNS,
    StructuredDatasetError,
    generate_controlled_structured_rows,
    load_structured_dataset,
    structured_dataset_report,
    validate_structured_rows,
    write_structured_dataset,
)

ML_ROOT = Path(__file__).resolve().parents[1]
CONTROLLED_ROOT = ML_ROOT / "data" / "controlled"
SOURCE_MANIFEST = CONTROLLED_ROOT / "manifest.csv"
STRUCTURED_CSV = CONTROLLED_ROOT / "structured_features.csv"


def test_committed_structured_dataset_is_current_and_group_safe() -> None:
    dataset = load_structured_dataset(path=STRUCTURED_CSV, source_manifest_path=SOURCE_MANIFEST)
    report = structured_dataset_report(dataset)

    assert (
        dataset.dataset_hash == "30a74b15fe34ef229edd7b28d25b334add7d79e2a73d06d9baae3ba560dda07f"
    )
    assert report["record_count"] == 18
    assert report["group_count"] == 6
    assert report["split_counts"] == {"test": 3, "train": 12, "validation": 3}
    assert report["training_executed"] is False
    groups_by_split = {
        split: {row["source_group_id"] for row in dataset.rows if row["split"] == split}
        for split in ("train", "validation", "test")
    }
    assert not groups_by_split["train"] & groups_by_split["validation"]
    assert not groups_by_split["train"] & groups_by_split["test"]
    assert not groups_by_split["validation"] & groups_by_split["test"]


def test_regeneration_is_reproducible(tmp_path: Path) -> None:
    first = write_structured_dataset(
        source_manifest_path=SOURCE_MANIFEST,
        output_path=tmp_path / "first.csv",
    )
    second = write_structured_dataset(
        source_manifest_path=SOURCE_MANIFEST,
        output_path=tmp_path / "second.csv",
    )

    assert first.dataset_hash == second.dataset_hash
    assert first.path.read_bytes() == second.path.read_bytes()


def test_each_partition_contains_every_class() -> None:
    dataset = load_structured_dataset(path=STRUCTURED_CSV, source_manifest_path=SOURCE_MANIFEST)
    for split in ("train", "validation", "test"):
        frame, labels, groups, sample_ids = dataset.partition(split)
        assert tuple(frame.columns) == FEATURE_NAMES
        assert set(labels) == set(RISK_CLASSES)
        assert len(groups) == len(labels) == len(sample_ids)


def test_generation_rejects_leaking_source_manifest(tmp_path: Path) -> None:
    source = load_manifest(SOURCE_MANIFEST)
    records = list(source.records)
    records[1] = replace(records[1], split="test" if records[0].split != "test" else "train")
    from momo_fdvs_ml.manifest import write_manifest

    leaking = write_manifest(tmp_path / "manifest.csv", records)
    with pytest.raises(StructuredDatasetError, match="cross splits"):
        generate_controlled_structured_rows(leaking)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda rows: rows.append(dict(rows[0])), "duplicate"),
        (lambda rows: rows[0].update({"split": "other"}), "invalid structured split"),
        (lambda rows: rows[0].update({"label": "OTHER"}), "invalid structured label"),
        (
            lambda rows: rows[0].update({"label_provenance": "rule-output"}),
            "label provenance",
        ),
        (lambda rows: rows[0].pop("sample_id"), "missing provenance"),
    ],
)
def test_structured_validation_rejects_invalid_provenance(mutate, message: str) -> None:  # type: ignore[no-untyped-def]
    source = load_manifest(SOURCE_MANIFEST)
    rows = [dict(row) for row in generate_controlled_structured_rows(source)]
    mutate(rows)
    with pytest.raises(StructuredDatasetError, match=message):
        validate_structured_rows(rows)


def test_structured_validation_rejects_group_leakage() -> None:
    source = load_manifest(SOURCE_MANIFEST)
    rows = [dict(row) for row in generate_controlled_structured_rows(source)]
    group = rows[0]["source_group_id"]
    other = next(row for row in rows if row["source_group_id"] == group and row is not rows[0])
    other["split"] = "test" if rows[0]["split"] != "test" else "train"
    with pytest.raises(StructuredDatasetError, match="source group leakage"):
        validate_structured_rows(rows)


def test_loader_rejects_column_drift(tmp_path: Path) -> None:
    path = tmp_path / "drift.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*STRUCTURED_COLUMNS, "extra"])
        writer.writeheader()
    with pytest.raises(StructuredDatasetError, match="columns or ordering"):
        load_structured_dataset(path=path, source_manifest_path=SOURCE_MANIFEST)


def test_loader_rejects_invalid_numeric_value(tmp_path: Path) -> None:
    rows = list(csv.DictReader(STRUCTURED_CSV.read_text(encoding="utf-8").splitlines()))
    rows[0][FEATURE_NAMES[0]] = "not-a-number"
    path = tmp_path / "invalid.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=STRUCTURED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(StructuredDatasetError, match="must be numeric"):
        load_structured_dataset(path=path, source_manifest_path=SOURCE_MANIFEST)
