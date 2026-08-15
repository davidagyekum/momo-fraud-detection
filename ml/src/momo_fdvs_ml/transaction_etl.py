"""Restart-safe private CSV-to-Parquet transaction ETL for logical PR14."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import sys
import time
import uuid
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import pandas as pd

from momo_fdvs_ml.transaction_pipeline import (
    MODEL_FEATURES,
    PARTITIONS,
    CanonicalTransaction,
    StepStatistic,
    TransactionFeatureRecord,
    TransactionPipelineError,
    canonicalize_transaction,
    iter_causal_feature_records,
    plan_temporal_splits,
    source_mapping,
    validate_source_header,
)

CATEGORICAL_FEATURES: Final = (
    "transaction_type",
    "initiator_role",
    "recipient_role",
    "sequence_pattern",
)
NUMERIC_FEATURES: Final = tuple(
    feature for feature in MODEL_FEATURES if feature not in CATEGORICAL_FEATURES
)
PREPROCESSOR_VERSION: Final = "transaction-core-preprocessor-v1"
FEATURE_CONTRACT_VERSION: Final = "transaction-core-features-v1"


@dataclass(frozen=True)
class TransactionBuildSpec:
    """Exact registered input and output constraints for one source."""

    dataset_id: str
    source_sha256: str
    expected_row_count: int
    expected_positive_count: int
    minimum_partition_positives: int = 100
    shard_size: int = 100_000
    entrypoint: str | None = None


@dataclass(frozen=True)
class SourceScan:
    """First-pass aggregate validation result."""

    row_count: int
    positive_count: int
    step_statistics: tuple[StepStatistic, ...]


@dataclass(frozen=True)
class TrainingPreprocessor:
    """Train-only fitted neutral values and categorical vocabulary."""

    schema_version: str
    fit_partition: str
    numeric_neutral_values: Mapping[str, float]
    categorical_values: Mapping[str, tuple[str, ...]]
    training_row_count: int
    artifact_sha256: str

    def safe_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "fit_partition": self.fit_partition,
            "numeric_neutral_values": dict(self.numeric_neutral_values),
            "categorical_values": {
                key: list(values) for key, values in self.categorical_values.items()
            },
            "training_row_count": self.training_row_count,
            "artifact_sha256": self.artifact_sha256,
        }


@dataclass
class _PreprocessorAccumulator:
    row_count: int = 0
    numeric_sums: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    numeric_counts: Counter[str] = field(default_factory=Counter)
    categorical_values: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    def update(self, record: TransactionFeatureRecord) -> None:
        if record.partition != "train":
            raise TransactionPipelineError("preprocessing may be fit on the train partition only")
        self.row_count += 1
        for name in NUMERIC_FEATURES:
            value = record.features[name]
            if value is not None:
                self.numeric_sums[name] += float(str(value))
                self.numeric_counts[name] += 1
        for name in CATEGORICAL_FEATURES:
            self.categorical_values[name].add(str(record.features[name]))

    def freeze(self) -> TrainingPreprocessor:
        if self.row_count == 0:
            raise TransactionPipelineError("training preprocessor cannot be fit on zero rows")
        neutral = {
            name: (
                self.numeric_sums[name] / self.numeric_counts[name]
                if self.numeric_counts[name]
                else 0.0
            )
            for name in NUMERIC_FEATURES
        }
        categories = {
            name: tuple(sorted({*self.categorical_values[name], "__UNKNOWN__"}))
            for name in CATEGORICAL_FEATURES
        }
        payload: dict[str, object] = {
            "schema_version": PREPROCESSOR_VERSION,
            "fit_partition": "train",
            "numeric_neutral_values": neutral,
            "categorical_values": {key: list(values) for key, values in categories.items()},
            "training_row_count": self.row_count,
        }
        digest = _json_hash(payload)
        return TrainingPreprocessor(
            schema_version=PREPROCESSOR_VERSION,
            fit_partition="train",
            numeric_neutral_values=neutral,
            categorical_values=categories,
            training_row_count=self.row_count,
            artifact_sha256=digest,
        )


@dataclass
class _SafeEda:
    row_count: int = 0
    positive_count: int = 0
    amount_sum: float = 0.0
    amount_minimum: float | None = None
    amount_maximum: float | None = None
    transaction_types: Counter[str] = field(default_factory=Counter)

    def update(self, record: TransactionFeatureRecord) -> None:
        self.row_count += 1
        self.positive_count += record.label_is_fraud
        amount = float(str(record.features["amount"]))
        self.amount_sum += amount
        self.amount_minimum = (
            amount if self.amount_minimum is None else min(self.amount_minimum, amount)
        )
        self.amount_maximum = (
            amount if self.amount_maximum is None else max(self.amount_maximum, amount)
        )
        self.transaction_types[str(record.features["transaction_type"])] += 1

    def safe_dict(self) -> dict[str, object]:
        return {
            "row_count": self.row_count,
            "positive_count": self.positive_count,
            "prevalence": self.positive_count / self.row_count if self.row_count else 0.0,
            "amount": {
                "minimum": self.amount_minimum,
                "maximum": self.amount_maximum,
                "mean": self.amount_sum / self.row_count if self.row_count else None,
            },
            "transaction_type_counts": dict(sorted(self.transaction_types.items())),
        }


@dataclass
class _PartitionBuffer:
    partition: str
    root: Path
    shard_size: int
    features: list[dict[str, object]] = field(default_factory=list)
    labels: list[dict[str, int]] = field(default_factory=list)
    provenance: list[dict[str, str]] = field(default_factory=list)
    shard_index: int = 0
    row_count: int = 0
    positive_count: int = 0
    row_id_hasher: object = field(default_factory=hashlib.sha256)
    shards: list[dict[str, object]] = field(default_factory=list)

    def append(self, record: TransactionFeatureRecord) -> None:
        self.features.append(dict(record.features))
        self.labels.append({"label_is_fraud": record.label_is_fraud})
        self.provenance.append(
            {
                "source_row_id": record.source_row_id,
                "dataset_source": record.dataset_source,
                "partition": record.partition,
            }
        )
        self.row_count += 1
        self.positive_count += record.label_is_fraud
        self.row_id_hasher.update(f"{record.source_row_id}\n".encode())  # type: ignore[attr-defined]
        if len(self.features) >= self.shard_size:
            self.flush()

    def flush(self) -> None:
        if not self.features:
            return
        prefix = f"part-{self.shard_index:05d}"
        paths = {
            "features": self.root / self.partition / "features" / f"{prefix}.parquet",
            "labels": self.root / self.partition / "labels" / f"{prefix}.parquet",
            "provenance": self.root / self.partition / "provenance" / f"{prefix}.parquet",
        }
        _write_parquet(paths["features"], self.features, columns=MODEL_FEATURES)
        _write_parquet(paths["labels"], self.labels, columns=("label_is_fraud",))
        _write_parquet(
            paths["provenance"],
            self.provenance,
            columns=("source_row_id", "dataset_source", "partition"),
        )
        self.shards.append(
            {
                "index": self.shard_index,
                "row_count": len(self.features),
                "features_sha256": _file_hash(paths["features"]),
                "labels_sha256": _file_hash(paths["labels"]),
                "provenance_sha256": _file_hash(paths["provenance"]),
            }
        )
        self.shard_index += 1
        self.features.clear()
        self.labels.clear()
        self.provenance.clear()

    def safe_dict(self) -> dict[str, object]:
        self.flush()
        return {
            "partition": self.partition,
            "sealed": self.partition == "locked_test",
            "row_count": self.row_count,
            "positive_count": self.positive_count,
            "prevalence": self.positive_count / self.row_count if self.row_count else 0.0,
            "row_id_sequence_sha256": self.row_id_hasher.hexdigest(),  # type: ignore[attr-defined]
            "shards": self.shards,
        }


def _json_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _peak_memory_bytes() -> int | None:
    if sys.platform == "win32":
        return None
    try:
        import resource

        maximum_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except (ImportError, OSError):
        return None
    multiplier = 1 if sys.platform == "darwin" else 1024
    return int(maximum_rss * multiplier)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _write_parquet(
    path: Path, rows: Sequence[Mapping[str, object]], *, columns: Sequence[str]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".parquet.tmp")
    frame = pd.DataFrame(rows, columns=list(columns))
    try:
        frame.to_parquet(temporary, engine="pyarrow", compression="snappy", index=False)
    except (ImportError, OSError, ValueError) as exc:
        raise TransactionPipelineError(f"unable to write governed Parquet shard: {exc}") from exc
    os.replace(temporary, path)


@contextmanager
def _open_transaction_csv(path: Path, *, entrypoint: str | None) -> Iterator[io.TextIOBase]:
    if entrypoint is None:
        with path.open("r", encoding="utf-8", newline="") as handle:
            yield handle
        return
    if not entrypoint or entrypoint.startswith(("/", "\\")) or ".." in Path(entrypoint).parts:
        raise TransactionPipelineError("archive entrypoint is unsafe")
    try:
        with zipfile.ZipFile(path) as archive:
            matches = [info for info in archive.infolist() if info.filename == entrypoint]
            if len(matches) != 1 or matches[0].is_dir():
                raise TransactionPipelineError(
                    "archive entrypoint is missing, duplicated or not a file"
                )
            with (
                archive.open(matches[0], "r") as binary,
                io.TextIOWrapper(binary, encoding="utf-8", newline="") as text,
            ):
                yield text
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise TransactionPipelineError(
            f"unable to open registered transaction archive: {exc}"
        ) from exc


def _iter_canonical_csv(
    path: Path, *, spec: TransactionBuildSpec
) -> Iterator[CanonicalTransaction]:
    mapping = source_mapping(spec.dataset_id)
    previous_step: int | None = None
    try:
        with _open_transaction_csv(path, entrypoint=spec.entrypoint) as handle:
            reader = csv.DictReader(handle)
            validate_source_header(mapping, reader.fieldnames or ())
            for row_number, raw in enumerate(reader, start=1):
                row = canonicalize_transaction(
                    raw,
                    mapping=mapping,
                    source_sha256=spec.source_sha256,
                    source_row_number=row_number,
                )
                if previous_step is not None and row.step < previous_step:
                    raise TransactionPipelineError(
                        "registered transaction source is not ordered by non-decreasing step"
                    )
                previous_step = row.step
                yield row
    except (OSError, UnicodeError, csv.Error) as exc:
        raise TransactionPipelineError(
            f"unable to read registered transaction source: {exc}"
        ) from exc


def scan_transaction_source(path: Path, *, spec: TransactionBuildSpec) -> SourceScan:
    """Hash and aggregate a registered source without retaining rows or actor IDs."""

    if _file_hash(path) != spec.source_sha256:
        raise TransactionPipelineError("transaction source SHA-256 does not match registration")
    by_step: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    row_count = 0
    positive_count = 0
    for row in _iter_canonical_csv(path, spec=spec):
        row_count += 1
        positive_count += row.label_is_fraud
        by_step[row.step][0] += 1
        by_step[row.step][1] += row.label_is_fraud
    if row_count != spec.expected_row_count or positive_count != spec.expected_positive_count:
        raise TransactionPipelineError("transaction source counts drifted from registration")
    return SourceScan(
        row_count=row_count,
        positive_count=positive_count,
        step_statistics=tuple(
            StepStatistic(step, counts[0], counts[1]) for step, counts in sorted(by_step.items())
        ),
    )


def transaction_feature_contract() -> dict[str, object]:
    """Publish inference timing, types, missing behavior and forbidden fields."""

    features = []
    nullable = {
        "time_since_previous",
        "prior_24h_mean",
        "prior_24h_median",
        "amount_to_prior_median",
    }
    for name in MODEL_FEATURES:
        features.append(
            {
                "name": name,
                "kind": "categorical" if name in CATEGORICAL_FEATURES else "numeric",
                "required": True,
                "nullable_before_preprocessing": name in nullable,
                "availability": (
                    "current_transaction" if name in MODEL_FEATURES[:8] else "strictly_prior_steps"
                ),
            }
        )
    return {
        "schema_version": FEATURE_CONTRACT_VERSION,
        "features": features,
        "forbidden": [
            "target_or_target_derived",
            "raw_actor_identifiers",
            "dataset_source_as_model_input",
            "PaySim_isFlaggedFraud",
            "origin_or_destination_balance_fields",
            "current_or_future_history",
            "invented_missing_context",
        ],
        "no_history_behavior": (
            "nullable summary plus explicit missing indicators; train-fitted neutral value only "
            "during preprocessing"
        ),
        "screenshot_only_supported": False,
    }


def fit_training_preprocessor(
    records: Iterable[TransactionFeatureRecord],
) -> TrainingPreprocessor:
    accumulator = _PreprocessorAccumulator()
    for record in records:
        accumulator.update(record)
    return accumulator.freeze()


def transform_features(
    features: Mapping[str, object], *, preprocessor: TrainingPreprocessor
) -> dict[str, object]:
    """Apply a frozen train-only contract without refitting on later partitions."""

    if tuple(features) != MODEL_FEATURES:
        raise TransactionPipelineError("feature row does not match the inference contract")
    transformed: dict[str, object] = {}
    for name in MODEL_FEATURES:
        value = features[name]
        if name in CATEGORICAL_FEATURES:
            text = str(value)
            transformed[name] = (
                text if text in preprocessor.categorical_values[name] else "__UNKNOWN__"
            )
        else:
            transformed[name] = (
                preprocessor.numeric_neutral_values[name] if value is None else float(str(value))
            )
    return transformed


def build_transaction_parquet_dataset(
    *, source_path: Path, output_path: Path, spec: TransactionBuildSpec
) -> dict[str, object]:
    """Build private frozen Parquet shards atomically without executing training."""

    if spec.shard_size < 1:
        raise TransactionPipelineError("shard_size must be positive")
    if output_path.exists():
        raise TransactionPipelineError("frozen transaction output already exists")
    scan = scan_transaction_source(source_path, spec=spec)
    split_plan = plan_temporal_splits(
        dataset_id=spec.dataset_id,
        source_sha256=spec.source_sha256,
        step_statistics=scan.step_statistics,
        minimum_positive_count=spec.minimum_partition_positives,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    staging = output_path.parent / f".{output_path.name}.tmp-{uuid.uuid4().hex}"
    started = time.perf_counter()
    try:
        buffers = {
            partition: _PartitionBuffer(partition, staging, spec.shard_size)
            for partition in PARTITIONS
        }
        preprocessor_accumulator = _PreprocessorAccumulator()
        safe_eda = {name: _SafeEda() for name in ("train", "tuning")}
        for record in iter_causal_feature_records(
            _iter_canonical_csv(source_path, spec=spec), split_plan=split_plan
        ):
            buffers[record.partition].append(record)
            if record.partition == "train":
                preprocessor_accumulator.update(record)
            if record.partition in safe_eda:
                safe_eda[record.partition].update(record)
        partition_reports = [buffers[name].safe_dict() for name in PARTITIONS]
        preprocessor = preprocessor_accumulator.freeze()
        _write_json(staging / "split-manifest.json", split_plan.safe_dict())
        _write_json(staging / "preprocessor.json", preprocessor.safe_dict())
        _write_json(staging / "feature-contract.json", transaction_feature_contract())
        peak_memory = _peak_memory_bytes()
        report_without_hash: dict[str, object] = {
            "schema_version": "transaction-etl-report-v1",
            "dataset_id": spec.dataset_id,
            "source_sha256": spec.source_sha256,
            "split_manifest_sha256": split_plan.manifest_sha256,
            "preprocessor_sha256": preprocessor.artifact_sha256,
            "row_count": scan.row_count,
            "positive_count": scan.positive_count,
            "partitions": partition_reports,
            "safe_eda": {name: summary.safe_dict() for name, summary in safe_eda.items()},
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "peak_memory_bytes": peak_memory,
            "peak_memory_measurement": (
                "process_max_rss" if peak_memory is not None else "unavailable_on_platform"
            ),
            "source_bytes_committed": False,
            "raw_actor_ids_exported_as_features": False,
            "locked_test_sealed": True,
            "locked_test_accessed_for_decisions": False,
            "training_executed": False,
        }
        report = {**report_without_hash, "report_sha256": _json_hash(report_without_hash)}
        _write_json(staging / "build-report.json", report)
        os.replace(staging, output_path)
        return report
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def load_non_test_partition(
    *, dataset_root: Path, partition: str, include_labels: bool = True
) -> tuple[pd.DataFrame, pd.Series[int] | None]:
    """Load only train/tuning/calibration shards; PR14 cannot open locked test."""

    if partition == "locked_test":
        raise TransactionPipelineError("locked test access is prohibited before PR20")
    if partition not in PARTITIONS:
        raise TransactionPipelineError("unknown transaction partition")
    feature_paths = sorted((dataset_root / partition / "features").glob("*.parquet"))
    label_paths = sorted((dataset_root / partition / "labels").glob("*.parquet"))
    if not feature_paths or (include_labels and len(feature_paths) != len(label_paths)):
        raise TransactionPipelineError("transaction partition shards are missing or incomplete")
    features = pd.concat((pd.read_parquet(path) for path in feature_paths), ignore_index=True)
    if tuple(features.columns) != MODEL_FEATURES:
        raise TransactionPipelineError("Parquet feature columns drifted from contract")
    labels = None
    if include_labels:
        label_frame = pd.concat((pd.read_parquet(path) for path in label_paths), ignore_index=True)
        if tuple(label_frame.columns) != ("label_is_fraud",) or len(label_frame) != len(features):
            raise TransactionPipelineError("Parquet label shards drifted from features")
        labels = label_frame["label_is_fraud"].astype(int)
    return features, labels
