from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from momo_fdvs_ml.image_schema import (
    IMAGE_CLASSES,
    IMAGE_INPUT_CHANNELS,
    IMAGE_INPUT_HEIGHT,
    IMAGE_INPUT_WIDTH,
    IMAGE_PREPROCESSING_SCHEMA_HASH,
    ImageDatasetError,
    governed_image_samples,
    image_dataset_report,
    preprocess_image_bytes,
    preprocess_image_path,
    preprocessing_schema_payload,
)
from momo_fdvs_ml.manifest import load_manifest

CONTROLLED_ROOT = Path(__file__).parents[1] / "data" / "controlled"
MANIFEST = CONTROLLED_ROOT / "manifest.csv"


def test_preprocessing_schema_is_stable_and_training_only() -> None:
    payload = preprocessing_schema_payload()
    assert IMAGE_PREPROCESSING_SCHEMA_HASH == (
        "8510a396d3115887f8ebff88414f75f9ea5b353f375d93cfdf65f488d55df616"
    )
    assert payload["augmentation"]["training_only"] is True  # type: ignore[index]
    assert "test" in payload["augmentation"]["forbidden"]  # type: ignore[index]
    assert payload["classes"] == list(IMAGE_CLASSES)


def test_controlled_manifest_projects_to_disjoint_binary_partitions() -> None:
    manifest = load_manifest(MANIFEST)
    samples = governed_image_samples(manifest, root=CONTROLLED_ROOT)
    assert len(samples) == 12
    assert {sample.label for sample in samples} == set(IMAGE_CLASSES)
    groups = {
        split: {sample.source_group_id for sample in samples if sample.split == split}
        for split in ("train", "validation", "test")
    }
    assert groups["train"].isdisjoint(groups["validation"])
    assert groups["train"].isdisjoint(groups["test"])
    assert groups["validation"].isdisjoint(groups["test"])


def test_dataset_report_is_honest_and_reproducible() -> None:
    first = image_dataset_report(MANIFEST, root=CONTROLLED_ROOT)
    second = image_dataset_report(MANIFEST, root=CONTROLLED_ROOT)
    assert first == second
    assert first["split_counts"] == {"test": 2, "train": 8, "validation": 2}
    assert first["training_executed"] is False
    assert first["model_metrics"] is None
    assert all(not values for values in first["group_intersections"].values())  # type: ignore[union-attr]


def test_preprocess_path_and_bytes_are_identical() -> None:
    path = CONTROLLED_ROOT / "images" / "controlled-original-0001.png"
    from_path = preprocess_image_path(path)
    from_bytes = preprocess_image_bytes(path.read_bytes())
    assert np.array_equal(from_path, from_bytes)
    assert from_path.shape == (IMAGE_INPUT_HEIGHT, IMAGE_INPUT_WIDTH, IMAGE_INPUT_CHANNELS)
    assert from_path.dtype == np.float32
    assert float(from_path.min()) >= -1.0
    assert float(from_path.max()) <= 1.0


def test_preprocess_normalises_exact_rgb_values(tmp_path: Path) -> None:
    path = tmp_path / "solid.png"
    Image.new("RGB", (300, 400), (0, 127, 255)).save(path)
    tensor = preprocess_image_path(path)
    assert tensor[0, 0].tolist() == pytest.approx([-1.0, 127 / 127.5 - 1.0, 1.0])


@pytest.mark.parametrize("payload", [b"", b"not-an-image"])
def test_preprocess_rejects_empty_or_corrupt_payload(payload: bytes) -> None:
    with pytest.raises(ImageDatasetError):
        preprocess_image_bytes(payload)


def test_report_matches_recorded_file() -> None:
    recorded = json.loads((CONTROLLED_ROOT / "image_dataset_report.json").read_text())
    assert recorded == image_dataset_report(MANIFEST, root=CONTROLLED_ROOT)
