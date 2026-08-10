"""Canonical image-model schema, governed sample index and deterministic preprocessing."""

from __future__ import annotations

import hashlib
import io
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from momo_fdvs_ml.manifest import DatasetManifest, ManifestError, load_manifest, validate_manifest

IMAGE_INPUT_HEIGHT: Final = 224
IMAGE_INPUT_WIDTH: Final = 224
IMAGE_INPUT_CHANNELS: Final = 3
IMAGE_CLASSES: Final = ("ORIGINAL", "CONTROLLED_TAMPERED")
IMAGE_LABEL_INDEX: Final = {"genuine": 0, "fraudulent": 1}
CANONICAL_IMAGE_LABELS: Final = ("unaltered", "tampered")
LEGACY_TO_CANONICAL_IMAGE_LABEL: Final = {
    "genuine": "unaltered",
    "fraudulent": "tampered",
    "ORIGINAL": "unaltered",
    "CONTROLLED_TAMPERED": "tampered",
}
IMAGE_PREPROCESSING_VERSION: Final = "image-rgb224-minus1-to1-v1"
IMAGE_DATASET_SCHEMA_VERSION: Final = "controlled-image-binary-v1"
IMAGE_MODEL_NAME: Final = "momo-fdvs-controlled-tamper"
IMAGE_RANDOM_SEED: Final = 20260812


class ImageDatasetError(RuntimeError):
    """Raised when governed image-model input is unsafe or inconsistent."""


def validate_canonical_image_label(value: str) -> str:
    """Accept only the manipulation taxonomy used by newly governed datasets."""

    if value not in CANONICAL_IMAGE_LABELS:
        raise ImageDatasetError("canonical image label must be unaltered or tampered")
    return value


def project_legacy_image_label(value: str) -> str:
    """Project existing controlled manifests/models without silently relabelling artifacts."""

    try:
        return LEGACY_TO_CANONICAL_IMAGE_LABEL[value]
    except KeyError as exc:
        raise ImageDatasetError("unsupported legacy image label") from exc


@dataclass(frozen=True)
class ImageSample:
    """One manifest record projected into the binary image task."""

    sample_id: str
    source_group_id: str
    split: str
    label: str
    label_index: int
    path: Path
    sha256: str
    source_type: str


def preprocessing_schema_payload() -> dict[str, object]:
    """Return the immutable preprocessing and augmentation contract."""

    return {
        "version": IMAGE_PREPROCESSING_VERSION,
        "input": {
            "height": IMAGE_INPUT_HEIGHT,
            "width": IMAGE_INPUT_WIDTH,
            "channels": IMAGE_INPUT_CHANNELS,
            "colour_mode": "RGB",
            "exif_orientation": "transpose_before_colour_conversion",
            "resize": "Pillow_BILINEAR",
            "dtype": "float32",
            "normalisation": "pixel / 127.5 - 1.0",
            "range": [-1.0, 1.0],
        },
        "classes": list(IMAGE_CLASSES),
        "positive_class": "CONTROLLED_TAMPERED",
        "augmentation": {
            "training_only": True,
            "seed": IMAGE_RANDOM_SEED,
            "operations": [
                {"name": "RandomRotation", "factor": 0.02},
                {"name": "RandomZoom", "height_factor": 0.05, "width_factor": 0.05},
                {"name": "RandomContrast", "factor": 0.08},
                {"name": "RandomTranslation", "height_factor": 0.02, "width_factor": 0.02},
            ],
            "forbidden": ["horizontal_flip", "vertical_flip", "validation", "test"],
        },
    }


def _canonical_hash(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


IMAGE_PREPROCESSING_SCHEMA_HASH: Final = _canonical_hash(preprocessing_schema_payload())


def _decode_image(stream: io.BytesIO | Path) -> Image.Image:
    try:
        with Image.open(stream) as source:
            source.load()
            oriented = ImageOps.exif_transpose(source)
            rgb = oriented.convert("RGB")
            return rgb.resize(
                (IMAGE_INPUT_WIDTH, IMAGE_INPUT_HEIGHT),
                resample=Image.Resampling.BILINEAR,
            )
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise ImageDatasetError("image cannot be decoded for deterministic preprocessing") from exc


def preprocess_image_bytes(payload: bytes) -> np.ndarray:
    """Decode hostile bytes deterministically into one normalised RGB tensor."""

    if not payload:
        raise ImageDatasetError("image payload is empty")
    image = _decode_image(io.BytesIO(payload))
    array = np.asarray(image, dtype=np.float32)
    expected = (IMAGE_INPUT_HEIGHT, IMAGE_INPUT_WIDTH, IMAGE_INPUT_CHANNELS)
    if array.shape != expected:
        raise ImageDatasetError("preprocessed image has an invalid tensor shape")
    normalised = array / np.float32(127.5) - np.float32(1.0)
    if not np.isfinite(normalised).all():
        raise ImageDatasetError("preprocessed image contains non-finite values")
    return normalised


def preprocess_image_path(path: Path) -> np.ndarray:
    """Read and preprocess one private or governed local image."""

    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ImageDatasetError("image cannot be read for deterministic preprocessing") from exc
    return preprocess_image_bytes(payload)


def governed_image_samples(manifest: DatasetManifest, *, root: Path) -> tuple[ImageSample, ...]:
    """Validate the manifest and project it into the controlled binary task."""

    validation = validate_manifest(manifest, root=root)
    try:
        validation.raise_for_errors()
    except ManifestError as exc:
        raise ImageDatasetError(str(exc)) from exc
    samples: list[ImageSample] = []
    for record in manifest.records:
        if record.label not in IMAGE_LABEL_INDEX:
            raise ImageDatasetError(f"unsupported image label for {record.sample_id}")
        if not record.relative_path or record.private_object_id:
            raise ImageDatasetError(
                "P12 controlled training requires repository-safe manifest image paths"
            )
        candidate = (root / record.relative_path).resolve()
        if not candidate.is_relative_to(root.resolve()):
            raise ImageDatasetError("image path escapes the governed dataset root")
        samples.append(
            ImageSample(
                sample_id=record.sample_id,
                source_group_id=record.source_group_id,
                split=record.split,
                label=IMAGE_CLASSES[IMAGE_LABEL_INDEX[record.label]],
                label_index=IMAGE_LABEL_INDEX[record.label],
                path=candidate,
                sha256=record.sha256,
                source_type=record.source_type,
            )
        )
    for split in ("train", "validation", "test"):
        labels = {sample.label for sample in samples if sample.split == split}
        if labels != set(IMAGE_CLASSES):
            raise ImageDatasetError(f"{split} must contain both binary image classes")
    return tuple(samples)


def image_dataset_report(manifest_path: Path, *, root: Path) -> dict[str, object]:
    """Create the canonical P12 dataset/preprocessing preflight report."""

    manifest = load_manifest(manifest_path)
    samples = governed_image_samples(manifest, root=root)
    group_splits: dict[str, set[str]] = {}
    for sample in samples:
        group_splits.setdefault(sample.source_group_id, set()).add(sample.split)
    intersections = {
        f"{left}_{right}": sorted(
            {sample.source_group_id for sample in samples if sample.split == left}
            & {sample.source_group_id for sample in samples if sample.split == right}
        )
        for left, right in (("train", "validation"), ("train", "test"), ("validation", "test"))
    }
    if any(intersections.values()) or any(len(value) != 1 for value in group_splits.values()):
        raise ImageDatasetError("source groups cross frozen image partitions")
    return {
        "schema_version": IMAGE_DATASET_SCHEMA_VERSION,
        "dataset_scope": "controlled_synthetic_only",
        "manifest_hash": manifest.manifest_hash,
        "split_hash": manifest.split_hash,
        "preprocessing_version": IMAGE_PREPROCESSING_VERSION,
        "preprocessing_schema_hash": IMAGE_PREPROCESSING_SCHEMA_HASH,
        "random_seed": IMAGE_RANDOM_SEED,
        "record_count": len(samples),
        "source_group_count": len(group_splits),
        "split_counts": dict(sorted(Counter(sample.split for sample in samples).items())),
        "label_counts": dict(sorted(Counter(sample.label for sample in samples).items())),
        "source_type_counts": dict(
            sorted(Counter(sample.source_type for sample in samples).items())
        ),
        "split_label_counts": {
            split: dict(
                sorted(Counter(sample.label for sample in samples if sample.split == split).items())
            )
            for split in ("train", "validation", "test")
        },
        "group_intersections": intersections,
        "augmentation_training_only": True,
        "report_scope": "dataset_preflight_only",
        "training_executed_by_report": False,
        "model_metrics_embedded": False,
        "limitations": [
            "Only six controlled source groups and twelve generic images are available.",
            "Labels represent declared controlled edits, not naturally occurring provider fraud.",
            "External training-run metrics are recorded separately under docs/evidence "
            "and are not embedded in this deterministic dataset report.",
        ],
    }


def write_image_dataset_report(manifest_path: Path, *, root: Path, output: Path) -> None:
    report = image_dataset_report(manifest_path, root=root)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
