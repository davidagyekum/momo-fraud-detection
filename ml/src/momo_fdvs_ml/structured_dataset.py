"""Controlled structured-feature rows derived from governed P10 source groups."""

from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pandas as pd

from momo_fdvs_ml.feature_schema import (
    FEATURE_NAMES,
    RISK_CLASSES,
    STRUCTURED_FEATURE_SCHEMA_HASH,
    STRUCTURED_FEATURE_SCHEMA_VERSION,
    validate_feature_row,
)
from momo_fdvs_ml.manifest import DatasetManifest, load_manifest

STRUCTURED_DATASET_VERSION: Final = "controlled-structured-evidence-v1"
STRUCTURED_DATASET_SEED: Final = 20260811
PROVENANCE_COLUMNS: Final = (
    "sample_id",
    "source_group_id",
    "split",
    "label",
    "label_provenance",
)
STRUCTURED_COLUMNS: Final = (*PROVENANCE_COLUMNS, *FEATURE_NAMES)


class StructuredDatasetError(ValueError):
    """Raised when controlled structured rows violate split or schema policy."""


@dataclass(frozen=True)
class StructuredDataset:
    """Validated structured rows and their immutable canonical hash."""

    path: Path
    rows: tuple[dict[str, object], ...]
    dataset_hash: str
    source_manifest_hash: str
    source_split_hash: str

    def partition(
        self, split: str
    ) -> tuple[pd.DataFrame, pd.Series[str], tuple[str, ...], tuple[str, ...]]:
        selected = [row for row in self.rows if row["split"] == split]
        if not selected:
            raise StructuredDatasetError(f"structured {split} partition is empty")
        frame = pd.DataFrame(
            [{name: row[name] for name in FEATURE_NAMES} for row in selected],
            columns=list(FEATURE_NAMES),
        )
        labels = pd.Series([str(row["label"]) for row in selected], name="label")
        groups = tuple(str(row["source_group_id"]) for row in selected)
        sample_ids = tuple(str(row["sample_id"]) for row in selected)
        return frame, labels, groups, sample_ids


def _bounded(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return round(max(minimum, min(maximum, value)), 6)


def _jitter(rng: random.Random, width: float) -> float:
    return rng.uniform(-width, width)


def _common_features() -> dict[str, object]:
    return {
        "cnn_tamper_probability": None,
        "cnn_available": 0.0,
        "cnn_probability_missing": 1.0,
        "provider_code": "GENERIC_MOMO",
        "template_code": "GENERIC_V1",
        "image_evidence_status": "AVAILABLE",
        "ocr_engine_status": "AVAILABLE",
    }


def _scenario_features(label: str, *, seed: int) -> dict[str, object]:
    rng = random.Random(seed)  # noqa: S311 - deterministic controlled fixture
    common = _common_features()
    if label == "GENUINE":
        values: dict[str, object] = {
            "ocr_required_field_coverage": _bounded(0.97 + _jitter(rng, 0.015)),
            "ocr_mean_confidence": _bounded(0.94 + _jitter(rng, 0.02)),
            "ocr_min_critical_confidence": _bounded(0.89 + _jitter(rng, 0.03)),
            "ocr_provider_confidence": _bounded(0.92 + _jitter(rng, 0.025)),
            "critical_correction_count": 0.0,
            "total_correction_count": float(rng.randrange(0, 2)),
            "transaction_reference_valid": 1.0,
            "amount_valid": 1.0,
            "phone_valid": 1.0,
            "timestamp_valid": 1.0,
            "status_text_consistent": 1.0,
            "ocr_text_density": _bounded(0.72 + _jitter(rng, 0.04)),
            "template_anchor_coverage": _bounded(0.94 + _jitter(rng, 0.025)),
            "blur_variance": round(720 + _jitter(rng, 80), 3),
            "contrast_stddev": round(72 + _jitter(rng, 6), 3),
            "aspect_ratio_deviation": _bounded(0.018 + _jitter(rng, 0.008), 0, 5),
            "crop_proximity": _bounded(0.78 + _jitter(rng, 0.06)),
            "metadata_inconsistency_count": 0.0,
            "ela_mean": round(2.1 + _jitter(rng, 0.5), 4),
            "ela_p95": round(7.0 + _jitter(rng, 1.2), 4),
            "noise_regional_cv": _bounded(0.08 + _jitter(rng, 0.025), 0, 10),
            "text_baseline_deviation": _bounded(0.025 + _jitter(rng, 0.01), 0, 2),
            "text_size_cv": _bounded(0.09 + _jitter(rng, 0.025), 0, 10),
            "exact_duplicate_count": 0.0,
            "nearest_phash_distance": round(18 + _jitter(rng, 3), 3),
            "reference_candidate_found": 1.0,
            "amount_match": 1.0,
            "currency_match": 1.0,
            "phone_match": 1.0,
            "name_similarity": _bounded(0.98 + _jitter(rng, 0.01)),
            "timestamp_difference_minutes": round(max(0, 2 + _jitter(rng, 1.5)), 3),
            "reference_status_match": 1.0,
            "verification_mismatch_count": 0.0,
            "reused_reference_count": 0.0,
            "nearest_phash_missing": 0.0,
            "reference_comparison_missing": 0.0,
            "name_similarity_missing": 0.0,
            "timestamp_difference_missing": 0.0,
            "verification_status": "VERIFIED",
        }
    elif label == "SUSPICIOUS":
        values = {
            "ocr_required_field_coverage": _bounded(0.62 + _jitter(rng, 0.08)),
            "ocr_mean_confidence": _bounded(0.56 + _jitter(rng, 0.07)),
            "ocr_min_critical_confidence": _bounded(0.31 + _jitter(rng, 0.08)),
            "ocr_provider_confidence": _bounded(0.48 + _jitter(rng, 0.08)),
            "critical_correction_count": float(rng.randrange(0, 2)),
            "total_correction_count": float(rng.randrange(1, 4)),
            "transaction_reference_valid": float(rng.randrange(0, 2)),
            "amount_valid": 1.0,
            "phone_valid": float(rng.randrange(0, 2)),
            "timestamp_valid": 1.0,
            "status_text_consistent": float(rng.randrange(0, 2)),
            "ocr_text_density": _bounded(0.42 + _jitter(rng, 0.08)),
            "template_anchor_coverage": _bounded(0.52 + _jitter(rng, 0.09)),
            "blur_variance": round(max(5, 135 + _jitter(rng, 35)), 3),
            "contrast_stddev": round(max(5, 31 + _jitter(rng, 7)), 3),
            "aspect_ratio_deviation": _bounded(0.19 + _jitter(rng, 0.07), 0, 5),
            "crop_proximity": _bounded(0.16 + _jitter(rng, 0.06)),
            "metadata_inconsistency_count": float(rng.randrange(0, 2)),
            "ela_mean": round(max(0, 5.5 + _jitter(rng, 1.4)), 4),
            "ela_p95": round(max(0, 15 + _jitter(rng, 3)), 4),
            "noise_regional_cv": _bounded(0.34 + _jitter(rng, 0.1), 0, 10),
            "text_baseline_deviation": _bounded(0.21 + _jitter(rng, 0.07), 0, 2),
            "text_size_cv": _bounded(0.31 + _jitter(rng, 0.08), 0, 10),
            "exact_duplicate_count": 0.0,
            "nearest_phash_distance": None,
            "reference_candidate_found": 0.0,
            "amount_match": None,
            "currency_match": None,
            "phone_match": None,
            "name_similarity": None,
            "timestamp_difference_minutes": None,
            "reference_status_match": None,
            "verification_mismatch_count": 0.0,
            "reused_reference_count": 0.0,
            "nearest_phash_missing": 1.0,
            "reference_comparison_missing": 1.0,
            "name_similarity_missing": 1.0,
            "timestamp_difference_missing": 1.0,
            "verification_status": "UNVERIFIED",
        }
    elif label == "FRAUDULENT":
        values = {
            "ocr_required_field_coverage": _bounded(0.88 + _jitter(rng, 0.04)),
            "ocr_mean_confidence": _bounded(0.76 + _jitter(rng, 0.05)),
            "ocr_min_critical_confidence": _bounded(0.63 + _jitter(rng, 0.06)),
            "ocr_provider_confidence": _bounded(0.81 + _jitter(rng, 0.04)),
            "critical_correction_count": float(rng.randrange(1, 4)),
            "total_correction_count": float(rng.randrange(2, 6)),
            "transaction_reference_valid": 1.0,
            "amount_valid": 1.0,
            "phone_valid": 1.0,
            "timestamp_valid": 1.0,
            "status_text_consistent": 0.0,
            "ocr_text_density": _bounded(0.68 + _jitter(rng, 0.05)),
            "template_anchor_coverage": _bounded(0.73 + _jitter(rng, 0.06)),
            "blur_variance": round(max(5, 510 + _jitter(rng, 90)), 3),
            "contrast_stddev": round(max(5, 54 + _jitter(rng, 8)), 3),
            "aspect_ratio_deviation": _bounded(0.09 + _jitter(rng, 0.04), 0, 5),
            "crop_proximity": _bounded(0.51 + _jitter(rng, 0.09)),
            "metadata_inconsistency_count": float(rng.randrange(1, 4)),
            "ela_mean": round(max(0, 28 + _jitter(rng, 5)), 4),
            "ela_p95": round(max(0, 76 + _jitter(rng, 10)), 4),
            "noise_regional_cv": _bounded(1.15 + _jitter(rng, 0.25), 0, 10),
            "text_baseline_deviation": _bounded(0.42 + _jitter(rng, 0.09), 0, 2),
            "text_size_cv": _bounded(0.71 + _jitter(rng, 0.12), 0, 10),
            "exact_duplicate_count": float(rng.randrange(0, 3)),
            "nearest_phash_distance": round(max(0, 2 + _jitter(rng, 1.2)), 3),
            "reference_candidate_found": 1.0,
            "amount_match": 0.0,
            "currency_match": 1.0,
            "phone_match": 0.0,
            "name_similarity": _bounded(0.42 + _jitter(rng, 0.1)),
            "timestamp_difference_minutes": round(max(0, 185 + _jitter(rng, 30)), 3),
            "reference_status_match": 0.0,
            "verification_mismatch_count": float(rng.randrange(3, 6)),
            "reused_reference_count": float(rng.randrange(1, 4)),
            "nearest_phash_missing": 0.0,
            "reference_comparison_missing": 0.0,
            "name_similarity_missing": 0.0,
            "timestamp_difference_missing": 0.0,
            "verification_status": "MISMATCH",
        }
    else:
        raise StructuredDatasetError(f"unsupported controlled label: {label}")
    values.update(common)
    return validate_feature_row(values)


def generate_controlled_structured_rows(
    manifest: DatasetManifest, *, seed: int = STRUCTURED_DATASET_SEED
) -> tuple[dict[str, object], ...]:
    """Create one declared scenario per class for each pre-split source group."""

    group_splits: dict[str, set[str]] = defaultdict(set)
    for record in manifest.records:
        group_splits[record.source_group_id].add(record.split)
    leaking = sorted(group for group, splits in group_splits.items() if len(splits) != 1)
    if leaking:
        raise StructuredDatasetError(
            f"source groups cross splits before structured generation: {', '.join(leaking)}"
        )

    rows: list[dict[str, object]] = []
    for group_index, group_id in enumerate(sorted(group_splits), start=1):
        split = next(iter(group_splits[group_id]))
        for label_index, label in enumerate(RISK_CLASSES, start=1):
            features = _scenario_features(label, seed=seed + group_index * 100 + label_index)
            rows.append(
                {
                    "sample_id": f"structured-{group_index:04d}-{label.lower()}",
                    "source_group_id": group_id,
                    "split": split,
                    "label": label,
                    "label_provenance": "declared-controlled-scenario-v1",
                    **features,
                }
            )
    return tuple(rows)


def _canonical_hash(rows: Iterable[dict[str, object]]) -> str:
    raw = json.dumps(list(rows), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def validate_structured_rows(rows: Iterable[dict[str, object]]) -> tuple[dict[str, object], ...]:
    """Reject duplicate samples, group leakage, schema drift and incomplete class splits."""

    materialised = tuple(rows)
    if not materialised:
        raise StructuredDatasetError("structured dataset is empty")
    seen_ids: set[str] = set()
    group_splits: dict[str, set[str]] = defaultdict(set)
    split_labels: dict[str, Counter[str]] = defaultdict(Counter)
    normalised: list[dict[str, object]] = []
    for row in materialised:
        missing_provenance = [name for name in PROVENANCE_COLUMNS if name not in row]
        if missing_provenance:
            raise StructuredDatasetError(
                f"missing provenance column(s): {', '.join(missing_provenance)}"
            )
        sample_id = str(row["sample_id"])
        if sample_id in seen_ids:
            raise StructuredDatasetError(f"duplicate structured sample_id: {sample_id}")
        seen_ids.add(sample_id)
        split = str(row["split"])
        if split not in {"train", "validation", "test"}:
            raise StructuredDatasetError(f"invalid structured split: {split}")
        label = str(row["label"])
        if label not in RISK_CLASSES:
            raise StructuredDatasetError(f"invalid structured label: {label}")
        if row["label_provenance"] != "declared-controlled-scenario-v1":
            raise StructuredDatasetError("controlled label provenance is missing or invalid")
        group_id = str(row["source_group_id"])
        group_splits[group_id].add(split)
        split_labels[split][label] += 1
        features = validate_feature_row({name: row[name] for name in FEATURE_NAMES})
        normalised.append(
            {
                "sample_id": sample_id,
                "source_group_id": group_id,
                "split": split,
                "label": label,
                "label_provenance": str(row["label_provenance"]),
                **features,
            }
        )
    leaking = [group for group, splits in group_splits.items() if len(splits) != 1]
    if leaking:
        raise StructuredDatasetError(
            f"structured source group leakage: {', '.join(sorted(leaking))}"
        )
    for split in ("train", "validation", "test"):
        missing_classes = sorted(set(RISK_CLASSES) - set(split_labels[split]))
        if missing_classes:
            raise StructuredDatasetError(
                f"{split} split is missing class(es): {', '.join(missing_classes)}"
            )
    return tuple(sorted(normalised, key=lambda row: str(row["sample_id"])))


def write_structured_dataset(
    *, source_manifest_path: Path, output_path: Path, seed: int = STRUCTURED_DATASET_SEED
) -> StructuredDataset:
    """Regenerate the committed controlled structured CSV from P10 groups."""

    source = load_manifest(source_manifest_path)
    rows = validate_structured_rows(generate_controlled_structured_rows(source, seed=seed))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=STRUCTURED_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {name: ("" if row[name] is None else row[name]) for name in STRUCTURED_COLUMNS}
            )
    return StructuredDataset(
        path=output_path,
        rows=rows,
        dataset_hash=_canonical_hash(rows),
        source_manifest_hash=source.manifest_hash,
        source_split_hash=source.split_hash,
    )


def _parse_csv_value(name: str, raw: str) -> object:
    if name in PROVENANCE_COLUMNS:
        return raw
    if name in {
        "provider_code",
        "template_code",
        "verification_status",
        "image_evidence_status",
        "ocr_engine_status",
    }:
        return raw
    if raw == "":
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise StructuredDatasetError(f"{name} must be numeric or empty") from exc


def load_structured_dataset(*, path: Path, source_manifest_path: Path) -> StructuredDataset:
    """Load, validate and bind a structured CSV to the governed P10 hashes."""

    source = load_manifest(source_manifest_path)
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != list(STRUCTURED_COLUMNS):
                raise StructuredDatasetError(
                    "structured CSV columns or ordering do not match schema"
                )
            rows = tuple(
                {name: _parse_csv_value(name, row[name]) for name in STRUCTURED_COLUMNS}
                for row in reader
            )
    except OSError as exc:
        raise StructuredDatasetError(f"unable to read structured dataset: {exc}") from exc
    validated = validate_structured_rows(rows)
    return StructuredDataset(
        path=path,
        rows=validated,
        dataset_hash=_canonical_hash(validated),
        source_manifest_hash=source.manifest_hash,
        source_split_hash=source.split_hash,
    )


def structured_dataset_report(dataset: StructuredDataset) -> dict[str, object]:
    """Return safe, reproducible counts and hashes without model metrics."""

    return {
        "dataset_version": STRUCTURED_DATASET_VERSION,
        "feature_schema_version": STRUCTURED_FEATURE_SCHEMA_VERSION,
        "feature_schema_hash": STRUCTURED_FEATURE_SCHEMA_HASH,
        "generation_seed": STRUCTURED_DATASET_SEED,
        "structured_dataset_hash": dataset.dataset_hash,
        "source_manifest_hash": dataset.source_manifest_hash,
        "source_split_hash": dataset.source_split_hash,
        "record_count": len(dataset.rows),
        "group_count": len({row["source_group_id"] for row in dataset.rows}),
        "split_counts": dict(sorted(Counter(str(row["split"]) for row in dataset.rows).items())),
        "label_counts": dict(sorted(Counter(str(row["label"]) for row in dataset.rows).items())),
        "scope": "controlled_synthetic_only",
        "training_executed": False,
        "limitations": [
            "Rows are deterministic controlled scenarios, not real provider transactions.",
            "Labels are declared scenario provenance, not outputs copied from fraud rules.",
            "The dataset is intentionally small and cannot estimate production prevalence.",
        ],
    }
