"""PR15 binary transaction-risk training, calibration, and trusted export."""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import os
import platform
import re
import statistics
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, cast

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    fbeta_score,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from momo_fdvs_ml.manifest import sha256_file
from momo_fdvs_ml.transaction_etl import (
    CATEGORICAL_FEATURES,
    FEATURE_CONTRACT_VERSION,
    NUMERIC_FEATURES,
    PREPROCESSOR_VERSION,
    load_non_test_partition,
)
from momo_fdvs_ml.transaction_pipeline import MODEL_FEATURES, TransactionPipelineError

ARTIFACT_FORMAT: Final = "momo-fdvs-transaction-core-joblib-v1"
REPORT_VERSION: Final = "transaction-core-training-report-v1"
MODEL_NAME: Final = "transaction_core"
MODEL_CONTRACT_VERSION: Final = "transaction-core-binary-risk-v1"
THRESHOLD_VERSION: Final = "transaction-core-risk-thresholds-v1"
CALIBRATION_VERSION: Final = "transaction-core-calibration-v1"
SEARCH_VERSION: Final = "transaction-core-search-v1"
SEEDS: Final = (42, 123, 2026)
SHA40: Final = re.compile(r"^[0-9a-f]{40}$")
SAFE_VERSION: Final = re.compile(r"^[a-z0-9][a-z0-9._-]{2,99}$")
MODEL_FAMILIES: Final = ("dummy", "logistic", "histogram", "xgboost", "forest")


class TransactionModelError(RuntimeError):
    """Raised when PR15 inputs, fitting evidence, or artifacts are unsafe."""


@dataclass(frozen=True)
class CandidateSpec:
    """One bounded model-family configuration."""

    family: str
    parameters: Mapping[str, object]

    def safe_dict(self) -> dict[str, object]:
        return {"family": self.family, "parameters": dict(self.parameters)}


@dataclass(frozen=True)
class TransactionTrainingConfig:
    """Versioned search, calibration, and threshold policy."""

    candidates: tuple[CandidateSpec, ...]
    seeds: tuple[int, ...] = SEEDS
    tuning_fpr_cap: float = 0.05
    medium_fpr_cap: float = 0.05
    high_precision_target: float = 0.90
    minimum_isotonic_positives: int = 200
    forest_max_rows: int = 500_000
    parity_rows: int = 128

    def safe_dict(self) -> dict[str, object]:
        return {
            "schema_version": SEARCH_VERSION,
            "candidates": [candidate.safe_dict() for candidate in self.candidates],
            "seeds": list(self.seeds),
            "tuning_fpr_cap": self.tuning_fpr_cap,
            "medium_fpr_cap": self.medium_fpr_cap,
            "high_precision_target": self.high_precision_target,
            "minimum_isotonic_positives": self.minimum_isotonic_positives,
            "forest_max_rows": self.forest_max_rows,
            "parity_rows": self.parity_rows,
        }

    @property
    def config_sha256(self) -> str:
        return _json_hash(self.safe_dict())


@dataclass(frozen=True)
class FrozenPreprocessor:
    """PR14 train-fitted neutral values and category vocabulary."""

    numeric_neutral_values: Mapping[str, float]
    categorical_values: Mapping[str, tuple[str, ...]]
    artifact_sha256: str
    training_row_count: int


@dataclass(frozen=True)
class PR14Bundle:
    """Verified safe metadata for a private PR14 feature bundle."""

    root: Path
    dataset_id: str
    source_sha256: str
    split_manifest_sha256: str
    preprocessor: FrozenPreprocessor
    build_report_sha256: str

    def safe_dict(self) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "source_sha256": self.source_sha256,
            "split_manifest_sha256": self.split_manifest_sha256,
            "preprocessor_sha256": self.preprocessor.artifact_sha256,
            "build_report_sha256": self.build_report_sha256,
        }


@dataclass(frozen=True)
class ThresholdArtifact:
    """Versioned medium/high risk thresholds selected without final-test access."""

    medium: float
    high: float
    medium_rule: str
    high_rule: str
    medium_f2: float
    medium_fpr: float
    high_precision: float
    high_recall: float

    def safe_dict(self) -> dict[str, object]:
        return {
            "schema_version": THRESHOLD_VERSION,
            "medium": self.medium,
            "high": self.high,
            "medium_rule": self.medium_rule,
            "high_rule": self.high_rule,
            "medium_f2": self.medium_f2,
            "medium_fpr": self.medium_fpr,
            "high_precision": self.high_precision,
            "high_recall": self.high_recall,
            "not_real_world_probability": True,
        }


@dataclass(frozen=True)
class BinaryCalibrator:
    """Serializable score-to-probability calibrator."""

    method: str
    estimator: Any

    def transform(
        self, probabilities: Sequence[float] | np.ndarray[Any, Any]
    ) -> np.ndarray[Any, Any]:
        values = np.asarray(probabilities, dtype=float).reshape(-1)
        if self.method == "sigmoid":
            matrix = cast(np.ndarray[Any, Any], self.estimator.predict_proba(values.reshape(-1, 1)))
            calibrated = matrix[:, 1]
        elif self.method == "isotonic":
            calibrated = np.asarray(self.estimator.predict(values), dtype=float)
        else:
            raise TransactionModelError("unknown transaction calibration method")
        if not np.all(np.isfinite(calibrated)):
            raise TransactionModelError("calibrator produced non-finite probabilities")
        return cast(np.ndarray[Any, Any], np.clip(calibrated, 0.0, 1.0))


@dataclass(frozen=True)
class TransactionTrainingOutputs:
    """Private artifact and safe aggregate PR15 evidence paths."""

    artifact_path: Path
    artifact_sha256: str
    report_path: Path
    model_card_path: Path
    registry_payload_path: Path
    run_manifest_path: Path
    report: Mapping[str, Any]


def default_training_config() -> TransactionTrainingConfig:
    """Return the bounded default search; maxima remain below the blueprint caps."""

    return TransactionTrainingConfig(
        candidates=(
            CandidateSpec("dummy", {"strategy": "prior"}),
            CandidateSpec("logistic", {"C": 0.1, "max_iter": 300}),
            CandidateSpec("logistic", {"C": 1.0, "max_iter": 300}),
            CandidateSpec("logistic", {"C": 10.0, "max_iter": 400}),
            CandidateSpec(
                "histogram", {"learning_rate": 0.05, "max_iter": 160, "max_leaf_nodes": 31}
            ),
            CandidateSpec(
                "histogram", {"learning_rate": 0.1, "max_iter": 120, "max_leaf_nodes": 31}
            ),
            CandidateSpec(
                "histogram", {"learning_rate": 0.05, "max_iter": 200, "max_leaf_nodes": 63}
            ),
            CandidateSpec(
                "xgboost",
                {"learning_rate": 0.05, "n_estimators": 300, "max_depth": 6},
            ),
            CandidateSpec(
                "xgboost",
                {"learning_rate": 0.1, "n_estimators": 220, "max_depth": 6},
            ),
            CandidateSpec(
                "xgboost",
                {"learning_rate": 0.05, "n_estimators": 350, "max_depth": 8},
            ),
            CandidateSpec("forest", {"n_estimators": 240, "max_depth": 18, "min_samples_leaf": 2}),
            CandidateSpec("forest", {"n_estimators": 320, "max_depth": 24, "min_samples_leaf": 1}),
        )
    )


def _validate_config(config: TransactionTrainingConfig) -> None:
    if not config.candidates:
        raise TransactionModelError("transaction search requires at least one candidate")
    counts = {family: 0 for family in MODEL_FAMILIES}
    for candidate in config.candidates:
        if candidate.family not in counts:
            raise TransactionModelError(f"unsupported transaction model family: {candidate.family}")
        counts[candidate.family] += 1
    maxima = {"dummy": 1, "logistic": 8, "histogram": 20, "xgboost": 30, "forest": 12}
    if any(counts[family] > maxima[family] for family in MODEL_FAMILIES):
        raise TransactionModelError("transaction candidate search exceeds the blueprint maxima")
    if config.seeds != SEEDS:
        raise TransactionModelError("transaction stability seeds must be exactly 42, 123, 2026")
    for value, name in (
        (config.tuning_fpr_cap, "tuning_fpr_cap"),
        (config.medium_fpr_cap, "medium_fpr_cap"),
        (config.high_precision_target, "high_precision_target"),
    ):
        if not 0 < value < 1:
            raise TransactionModelError(f"{name} must be between zero and one")
    if config.minimum_isotonic_positives < 1 or config.forest_max_rows < 1:
        raise TransactionModelError("calibration and forest limits must be positive")


def load_training_config(path: Path | None) -> TransactionTrainingConfig:
    """Load a strict JSON search configuration or return the versioned default."""

    if path is None:
        config = default_training_config()
        _validate_config(config)
        return config
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TransactionModelError("unable to read transaction training configuration") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "candidates",
        "seeds",
        "tuning_fpr_cap",
        "medium_fpr_cap",
        "high_precision_target",
        "minimum_isotonic_positives",
        "forest_max_rows",
        "parity_rows",
    }:
        raise TransactionModelError("transaction training configuration has unknown/missing fields")
    if payload["schema_version"] != SEARCH_VERSION or not isinstance(payload["candidates"], list):
        raise TransactionModelError("transaction training configuration version is unsupported")
    candidates: list[CandidateSpec] = []
    for item in payload["candidates"]:
        if not isinstance(item, dict) or set(item) != {"family", "parameters"}:
            raise TransactionModelError("transaction candidate configuration is malformed")
        family = item["family"]
        parameters = item["parameters"]
        if not isinstance(family, str) or not isinstance(parameters, dict):
            raise TransactionModelError("transaction candidate types are invalid")
        candidates.append(CandidateSpec(family, cast(Mapping[str, object], parameters)))
    try:
        config = TransactionTrainingConfig(
            candidates=tuple(candidates),
            seeds=tuple(_as_int(value) for value in cast(list[object], payload["seeds"])),
            tuning_fpr_cap=float(cast(float, payload["tuning_fpr_cap"])),
            medium_fpr_cap=float(cast(float, payload["medium_fpr_cap"])),
            high_precision_target=float(cast(float, payload["high_precision_target"])),
            minimum_isotonic_positives=_as_int(payload["minimum_isotonic_positives"]),
            forest_max_rows=_as_int(payload["forest_max_rows"]),
            parity_rows=_as_int(payload["parity_rows"]),
        )
    except (TypeError, ValueError) as exc:
        raise TransactionModelError(
            "transaction training configuration values are invalid"
        ) from exc
    _validate_config(config)
    return config


def _json_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _as_int(value: object) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError) as exc:
        raise TransactionModelError("expected an integer configuration value") from exc


def _as_float(value: object) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError) as exc:
        raise TransactionModelError("expected a numeric configuration value") from exc


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TransactionModelError(f"unable to read required PR15 JSON: {path.name}") from exc
    if not isinstance(payload, dict):
        raise TransactionModelError(f"required PR15 JSON is not an object: {path.name}")
    return cast(dict[str, Any], payload)


def _write_json_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _dump_joblib_atomic(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    joblib.dump(payload, temporary, compress=3)
    os.replace(temporary, path)
    return sha256_file(path)


def verify_pr14_bundle(dataset_root: Path) -> PR14Bundle:
    """Verify safe PR14 metadata and non-test shard hashes without opening locked test."""

    root = dataset_root.resolve()
    build_path = root / "build-report.json"
    build = _load_json(build_path)
    split = _load_json(root / "split-manifest.json")
    preprocessor = _load_json(root / "preprocessor.json")
    if build.get("schema_version") != "transaction-etl-report-v1":
        raise TransactionModelError("PR14 build report version is unsupported")
    if (
        build.get("locked_test_sealed") is not True
        or build.get("locked_test_accessed_for_decisions") is not False
        or build.get("training_executed") is not False
    ):
        raise TransactionModelError("PR14 bundle does not preserve the locked-test boundary")
    dataset_id = build.get("dataset_id")
    source_sha256 = build.get("source_sha256")
    split_sha256 = build.get("split_manifest_sha256")
    preprocessor_sha256 = build.get("preprocessor_sha256")
    if dataset_id not in {"paysim", "momtsim-v1", "momtsim-v2"}:
        raise TransactionModelError("PR14 dataset identity is unsupported")
    if not all(
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
        for value in (source_sha256, split_sha256, preprocessor_sha256)
    ):
        raise TransactionModelError("PR14 content identities are malformed")
    if split.get("manifest_sha256") != split_sha256 or split.get("dataset_id") != dataset_id:
        raise TransactionModelError("PR14 split manifest identity drifted")
    if split.get("locked_test_accessed_for_decisions") is not False:
        raise TransactionModelError("PR14 split manifest exposes the locked test")
    if (
        preprocessor.get("schema_version") != PREPROCESSOR_VERSION
        or preprocessor.get("fit_partition") != "train"
        or preprocessor.get("artifact_sha256") != preprocessor_sha256
    ):
        raise TransactionModelError("PR14 train-only preprocessor identity drifted")
    preprocessor_payload = {
        key: value for key, value in preprocessor.items() if key != "artifact_sha256"
    }
    if _json_hash(preprocessor_payload) != preprocessor_sha256:
        raise TransactionModelError("PR14 preprocessor content hash is invalid")
    numeric = preprocessor.get("numeric_neutral_values")
    categorical = preprocessor.get("categorical_values")
    if not isinstance(numeric, dict) or set(numeric) != set(NUMERIC_FEATURES):
        raise TransactionModelError("PR14 numeric preprocessor contract drifted")
    if not isinstance(categorical, dict) or set(categorical) != set(CATEGORICAL_FEATURES):
        raise TransactionModelError("PR14 categorical preprocessor contract drifted")
    frozen = FrozenPreprocessor(
        numeric_neutral_values={name: _as_float(numeric[name]) for name in NUMERIC_FEATURES},
        categorical_values={
            name: tuple(str(value) for value in categorical[name]) for name in CATEGORICAL_FEATURES
        },
        artifact_sha256=cast(str, preprocessor_sha256),
        training_row_count=_as_int(preprocessor.get("training_row_count", 0)),
    )
    if frozen.training_row_count < 1 or any(
        "__UNKNOWN__" not in frozen.categorical_values[name] for name in CATEGORICAL_FEATURES
    ):
        raise TransactionModelError("PR14 preprocessor is incomplete")
    reports = build.get("partitions")
    if not isinstance(reports, list):
        raise TransactionModelError("PR14 partition report is missing")
    report_by_name = {item.get("partition"): item for item in reports if isinstance(item, dict)}
    for partition in ("train", "tuning", "calibration"):
        report = report_by_name.get(partition)
        if not isinstance(report, dict) or report.get("sealed") is not False:
            raise TransactionModelError(f"PR14 {partition} partition metadata is invalid")
        shards = report.get("shards")
        if not isinstance(shards, list) or not shards:
            raise TransactionModelError(f"PR14 {partition} partition has no shards")
        for shard in shards:
            if not isinstance(shard, dict) or not isinstance(shard.get("index"), int):
                raise TransactionModelError("PR14 shard metadata is malformed")
            prefix = f"part-{shard['index']:05d}.parquet"
            for kind in ("features", "labels"):
                path = root / partition / kind / prefix
                expected = shard.get(f"{kind}_sha256")
                if not path.is_file() or sha256_file(path) != expected:
                    raise TransactionModelError(f"PR14 {partition} {kind} shard hash drifted")
    locked = report_by_name.get("locked_test")
    if not isinstance(locked, dict) or locked.get("sealed") is not True:
        raise TransactionModelError("PR14 locked-test partition is not sealed")
    return PR14Bundle(
        root=root,
        dataset_id=cast(str, dataset_id),
        source_sha256=cast(str, source_sha256),
        split_manifest_sha256=cast(str, split_sha256),
        preprocessor=frozen,
        build_report_sha256=sha256_file(build_path),
    )


def load_pr15_partition(bundle: PR14Bundle, partition: str) -> tuple[pd.DataFrame, pd.Series[int]]:
    """Load and normalize one permitted partition using the frozen PR14 preprocessor."""

    if partition not in {"train", "tuning", "calibration"}:
        raise TransactionModelError("PR15 may load only train, tuning, or calibration")
    try:
        features, labels = load_non_test_partition(
            dataset_root=bundle.root, partition=partition, include_labels=True
        )
    except TransactionPipelineError as exc:
        raise TransactionModelError(str(exc)) from exc
    if labels is None or set(int(value) for value in labels.unique()) - {0, 1}:
        raise TransactionModelError("transaction labels must be binary")
    transformed = apply_frozen_preprocessor(features, bundle.preprocessor)
    return transformed, labels.astype(np.int8)


def apply_frozen_preprocessor(
    frame: pd.DataFrame, preprocessor: FrozenPreprocessor
) -> pd.DataFrame:
    """Apply PR14 neutral values/vocabulary without fitting on later partitions."""

    if tuple(frame.columns) != MODEL_FEATURES:
        raise TransactionModelError("transaction feature frame drifted from the PR14 contract")
    transformed = pd.DataFrame(index=frame.index)
    for name in NUMERIC_FEATURES:
        values = pd.to_numeric(frame[name], errors="coerce")
        transformed[name] = values.fillna(preprocessor.numeric_neutral_values[name]).astype(
            np.float32
        )
    for name in CATEGORICAL_FEATURES:
        allowed = set(preprocessor.categorical_values[name])
        transformed[name] = frame[name].map(
            lambda value, allowed_values=allowed: (
                str(value) if str(value) in allowed_values else "__UNKNOWN__"
            )
        )
    return transformed.loc[:, list(MODEL_FEATURES)]


def _transformer(
    preprocessor: FrozenPreprocessor, *, scale_numeric: bool, dense: bool
) -> ColumnTransformer:
    numeric_transformer: object = StandardScaler() if scale_numeric else "passthrough"
    categories = [list(preprocessor.categorical_values[name]) for name in CATEGORICAL_FEATURES]
    categorical = OneHotEncoder(
        categories=categories,
        handle_unknown="ignore",
        sparse_output=not dense,
        dtype=np.float32,
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_transformer, list(NUMERIC_FEATURES)),
            ("categorical", categorical, list(CATEGORICAL_FEATURES)),
        ],
        remainder="drop",
        sparse_threshold=0.0 if dense else 1.0,
        verbose_feature_names_out=True,
    )


def build_candidate_pipeline(
    candidate: CandidateSpec,
    *,
    preprocessor: FrozenPreprocessor,
    random_seed: int,
    positive_weight: float,
) -> Pipeline:
    """Build one deterministic candidate adapter from a validated search spec."""

    parameters = dict(candidate.parameters)
    if candidate.family == "dummy":
        model: object = DummyClassifier(strategy=str(parameters.get("strategy", "prior")))
        dense = False
        scale = False
    elif candidate.family == "logistic":
        model = LogisticRegression(
            C=_as_float(parameters.get("C", 1.0)),
            max_iter=_as_int(parameters.get("max_iter", 300)),
            class_weight="balanced",
            solver="liblinear",
            random_state=random_seed,
        )
        dense = False
        scale = True
    elif candidate.family == "histogram":
        model = HistGradientBoostingClassifier(
            learning_rate=_as_float(parameters.get("learning_rate", 0.1)),
            max_iter=_as_int(parameters.get("max_iter", 120)),
            max_leaf_nodes=_as_int(parameters.get("max_leaf_nodes", 31)),
            class_weight="balanced",
            random_state=random_seed,
        )
        dense = True
        scale = False
    elif candidate.family == "forest":
        model = RandomForestClassifier(
            n_estimators=_as_int(parameters.get("n_estimators", 240)),
            max_depth=_as_int(parameters.get("max_depth", 18)),
            min_samples_leaf=_as_int(parameters.get("min_samples_leaf", 2)),
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=random_seed,
        )
        dense = False
        scale = False
    elif candidate.family == "xgboost":
        try:
            xgboost = importlib.import_module("xgboost")
        except ImportError as exc:
            raise TransactionModelError(
                "XGBoost candidate requested but the pinned training dependency is unavailable"
            ) from exc
        classifier = getattr(xgboost, "XGBClassifier", None)
        if classifier is None:
            raise TransactionModelError("installed XGBoost does not expose XGBClassifier")
        model = classifier(
            learning_rate=_as_float(parameters.get("learning_rate", 0.05)),
            n_estimators=_as_int(parameters.get("n_estimators", 300)),
            max_depth=_as_int(parameters.get("max_depth", 6)),
            objective="binary:logistic",
            eval_metric="logloss",
            tree_method="hist",
            scale_pos_weight=positive_weight,
            random_state=random_seed,
            n_jobs=2,
        )
        dense = False
        scale = False
    else:
        raise TransactionModelError(f"unsupported transaction model family: {candidate.family}")
    return Pipeline(
        steps=[
            (
                "features",
                _transformer(preprocessor, scale_numeric=scale, dense=dense),
            ),
            ("classifier", model),
        ]
    )


def _probabilities(model: Any, frame: pd.DataFrame) -> np.ndarray[Any, Any]:
    matrix = np.asarray(model.predict_proba(frame), dtype=float)
    classes = tuple(int(value) for value in model.classes_)
    if matrix.ndim != 2 or matrix.shape[1] != len(classes) or 1 not in classes:
        raise TransactionModelError("transaction candidate lacks a binary probability contract")
    values = matrix[:, classes.index(1)]
    if not np.all(np.isfinite(values)) or np.any((values < 0) | (values > 1)):
        raise TransactionModelError("transaction candidate produced invalid probabilities")
    return values


def binary_metrics(labels: Sequence[int], probabilities: Sequence[float]) -> dict[str, object]:
    """Compute ranking and fixed-0.5 diagnostics on a non-final partition."""

    truth = np.asarray(labels, dtype=int)
    scores = np.asarray(probabilities, dtype=float)
    if len(truth) != len(scores) or not len(truth) or set(truth.tolist()) != {0, 1}:
        raise TransactionModelError("binary metrics require aligned two-class evidence")
    predicted = (scores >= 0.5).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        truth, predicted, labels=[0, 1], zero_division=0
    )
    matrix = confusion_matrix(truth, predicted, labels=[0, 1])
    tn, fp, fn, tp = (int(value) for value in matrix.ravel())
    return {
        "row_count": len(truth),
        "positive_count": int(truth.sum()),
        "prevalence": round(float(truth.mean()), 8),
        "average_precision": round(float(average_precision_score(truth, scores)), 8),
        "roc_auc": round(float(roc_auc_score(truth, scores)), 8),
        "brier": round(float(brier_score_loss(truth, scores)), 8),
        "threshold_0_5": {
            "confusion_matrix_labels": [0, 1],
            "confusion_matrix": matrix.tolist(),
            "precision_positive": round(float(precision[1]), 8),
            "recall_positive": round(float(recall[1]), 8),
            "f1_positive": round(float(f1[1]), 8),
            "false_positive_rate": round(fp / (fp + tn), 8) if fp + tn else 0.0,
            "false_negative_rate": round(fn / (fn + tp), 8) if fn + tp else 0.0,
        },
    }


def _recall_under_fpr(
    labels: np.ndarray[Any, Any], scores: np.ndarray[Any, Any], cap: float
) -> float:
    best = 0.0
    for threshold in np.unique(scores):
        predicted = scores >= threshold
        tn, fp, fn, tp = (
            int(value) for value in confusion_matrix(labels, predicted, labels=[0, 1]).ravel()
        )
        fpr = fp / (fp + tn) if fp + tn else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        if fpr <= cap:
            best = max(best, recall)
    return best


def _candidate_rank(metrics: Mapping[str, object], operating_recall: float) -> tuple[float, ...]:
    return (
        _as_float(metrics["average_precision"]),
        operating_recall,
        -_as_float(metrics["brier"]),
    )


def _subset_for_candidate(
    frame: pd.DataFrame,
    labels: pd.Series[int],
    *,
    candidate: CandidateSpec,
    maximum_forest_rows: int,
    random_seed: int,
) -> tuple[pd.DataFrame, pd.Series[int], bool]:
    if candidate.family != "forest" or len(frame) <= maximum_forest_rows:
        return frame, labels, False
    positives = labels[labels == 1]
    negatives = labels[labels == 0]
    positive_target = min(len(positives), maximum_forest_rows // 2)
    negative_target = maximum_forest_rows - positive_target
    if len(negatives) < negative_target:
        negative_target = len(negatives)
        positive_target = min(len(positives), maximum_forest_rows - negative_target)
    selected = pd.concat(
        [
            positives.sample(n=positive_target, random_state=random_seed, replace=False),
            negatives.sample(n=negative_target, random_state=random_seed, replace=False),
        ]
    ).sort_index()
    return frame.loc[selected.index], labels.loc[selected.index], True


def _checkpoint_identity(
    *, bundle: PR14Bundle, config: TransactionTrainingConfig, candidate: CandidateSpec, seed: int
) -> str:
    return _json_hash(
        {
            **bundle.safe_dict(),
            "config_sha256": config.config_sha256,
            "candidate": candidate.safe_dict(),
            "seed": seed,
        }
    )


def _fit_or_resume_candidate(
    *,
    bundle: PR14Bundle,
    config: TransactionTrainingConfig,
    candidate: CandidateSpec,
    seed: int,
    train_x: pd.DataFrame,
    train_y: pd.Series[int],
    tuning_x: pd.DataFrame,
    tuning_y: pd.Series[int],
    checkpoint_root: Path,
) -> tuple[Any, dict[str, object]]:
    identity = _checkpoint_identity(bundle=bundle, config=config, candidate=candidate, seed=seed)
    model_path = checkpoint_root / f"{identity}.joblib"
    report_path = checkpoint_root / f"{identity}.json"
    if model_path.exists() or report_path.exists():
        if not model_path.is_file() or not report_path.is_file():
            raise TransactionModelError("candidate checkpoint is incomplete")
        checkpoint = _load_json(report_path)
        if checkpoint.get("identity_sha256") != identity:
            raise TransactionModelError("candidate checkpoint identity drifted")
        if sha256_file(model_path) != checkpoint.get("model_sha256"):
            raise TransactionModelError("candidate checkpoint hash drifted")
        try:
            model = joblib.load(model_path)
        except Exception as exc:
            raise TransactionModelError("unable to load verified candidate checkpoint") from exc
        return model, cast(dict[str, object], checkpoint["safe_result"])
    selected_x, selected_y, subset_applied = _subset_for_candidate(
        train_x,
        train_y,
        candidate=candidate,
        maximum_forest_rows=config.forest_max_rows,
        random_seed=seed,
    )
    positives = int(selected_y.sum())
    negatives = len(selected_y) - positives
    if positives == 0 or negatives == 0:
        raise TransactionModelError("candidate training requires both labels")
    model = build_candidate_pipeline(
        candidate,
        preprocessor=bundle.preprocessor,
        random_seed=seed,
        positive_weight=negatives / positives,
    )
    started = time.perf_counter()
    model.fit(selected_x, selected_y)
    tuning_scores = _probabilities(model, tuning_x)
    metrics = binary_metrics(tuning_y.tolist(), tuning_scores.tolist())
    operating_recall = _recall_under_fpr(
        tuning_y.to_numpy(dtype=int), tuning_scores, config.tuning_fpr_cap
    )
    safe_result: dict[str, object] = {
        "candidate": candidate.safe_dict(),
        "seed": seed,
        "training_row_count": len(selected_y),
        "training_positive_count": positives,
        "train_only_sampling_applied": subset_applied,
        "tuning_metrics": metrics,
        "recall_at_or_below_fpr_cap": round(operating_recall, 8),
        "fpr_cap": config.tuning_fpr_cap,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "locked_test_accessed": False,
    }
    model_sha256 = _dump_joblib_atomic(model_path, model)
    _write_json_atomic(
        report_path,
        {
            "schema_version": "transaction-candidate-checkpoint-v1",
            "identity_sha256": identity,
            "model_sha256": model_sha256,
            "safe_result": safe_result,
        },
    )
    return model, safe_result


def _fit_calibrator(
    method: str, raw_scores: np.ndarray[Any, Any], labels: np.ndarray[Any, Any]
) -> BinaryCalibrator:
    if set(labels.tolist()) != {0, 1}:
        raise TransactionModelError("calibration fit half must contain both labels")
    if method == "sigmoid":
        estimator = LogisticRegression(C=1_000_000.0, solver="lbfgs", max_iter=500)
        estimator.fit(raw_scores.reshape(-1, 1), labels)
        return BinaryCalibrator(method="sigmoid", estimator=estimator)
    if method == "isotonic":
        estimator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        estimator.fit(raw_scores, labels)
        return BinaryCalibrator(method="isotonic", estimator=estimator)
    raise TransactionModelError("unsupported transaction calibration method")


def calibrate_independently(
    model: Any,
    calibration_x: pd.DataFrame,
    calibration_y: pd.Series[int],
    *,
    minimum_isotonic_positives: int,
) -> tuple[BinaryCalibrator, np.ndarray[Any, Any], np.ndarray[Any, Any], dict[str, object]]:
    """Fit calibration on the first half and select it on the untouched second half."""

    if len(calibration_y) < 20:
        raise TransactionModelError("calibration partition is too small")
    boundary = len(calibration_y) // 2
    fit_y = calibration_y.iloc[:boundary].to_numpy(dtype=int)
    select_y = calibration_y.iloc[boundary:].to_numpy(dtype=int)
    if set(fit_y.tolist()) != {0, 1} or set(select_y.tolist()) != {0, 1}:
        raise TransactionModelError("both chronological calibration halves need both labels")
    raw_fit = _probabilities(model, calibration_x.iloc[:boundary])
    raw_select = _probabilities(model, calibration_x.iloc[boundary:])
    methods = ["sigmoid"]
    if int(fit_y.sum()) >= minimum_isotonic_positives:
        methods.append("isotonic")
    evaluated: list[tuple[float, float, str, BinaryCalibrator, np.ndarray[Any, Any]]] = []
    method_reports: list[dict[str, object]] = []
    for method in methods:
        calibrator = _fit_calibrator(method, raw_fit, fit_y)
        calibrated = calibrator.transform(raw_select)
        brier = float(brier_score_loss(select_y, calibrated))
        average_precision = float(average_precision_score(select_y, calibrated))
        evaluated.append((brier, -average_precision, method, calibrator, calibrated))
        method_reports.append(
            {
                "method": method,
                "selection_brier": round(brier, 8),
                "selection_average_precision": round(average_precision, 8),
            }
        )
    selected = min(evaluated, key=lambda item: (item[0], item[1], item[2]))
    report = {
        "schema_version": CALIBRATION_VERSION,
        "partition": "calibration",
        "chronological_fit_rows": boundary,
        "chronological_threshold_selection_rows": len(select_y),
        "fit_positive_count": int(fit_y.sum()),
        "threshold_selection_positive_count": int(select_y.sum()),
        "methods": method_reports,
        "selected_method": selected[2],
        "final_test_accessed": False,
    }
    return selected[3], selected[4], select_y, report


def _threshold_stats(
    labels: np.ndarray[Any, Any], scores: np.ndarray[Any, Any], threshold: float
) -> tuple[float, float, float, float]:
    predicted = scores >= threshold
    tn, fp, fn, tp = (
        int(value) for value in confusion_matrix(labels, predicted, labels=[0, 1]).ravel()
    )
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    f2 = float(fbeta_score(labels, predicted, beta=2, zero_division=0))
    return precision, recall, fpr, f2


def select_risk_thresholds(
    labels: Sequence[int],
    probabilities: Sequence[float],
    *,
    medium_fpr_cap: float,
    high_precision_target: float,
) -> ThresholdArtifact:
    """Select medium/high policies on calibration-selection rows only."""

    truth = np.asarray(labels, dtype=int)
    scores = np.asarray(probabilities, dtype=float)
    if len(truth) != len(scores) or set(truth.tolist()) != {0, 1}:
        raise TransactionModelError("threshold selection requires aligned two-class evidence")
    thresholds = sorted({0.0, 1.0, *(float(value) for value in scores)})
    evaluated = [
        (threshold, *_threshold_stats(truth, scores, threshold)) for threshold in thresholds
    ]
    feasible_medium = [row for row in evaluated if row[3] <= medium_fpr_cap]
    medium_rule = "maximize_f2_subject_to_fpr_cap"
    if not feasible_medium:
        feasible_medium = evaluated
        medium_rule = "fallback_maximize_f2_no_threshold_met_fpr_cap"
    medium_row = max(feasible_medium, key=lambda row: (row[4], row[2], -row[3], -row[0]))
    high_candidates = [
        row for row in evaluated if row[0] >= medium_row[0] and row[1] >= high_precision_target
    ]
    high_rule = "lowest_threshold_meeting_precision_target"
    if high_candidates:
        high_row = min(high_candidates, key=lambda row: row[0])
    else:
        eligible = [row for row in evaluated if row[0] >= medium_row[0]]
        high_row = max(eligible, key=lambda row: (row[1], row[2], row[0]))
        high_rule = "fallback_maximize_precision_target_unmet"
    return ThresholdArtifact(
        medium=round(float(medium_row[0]), 8),
        high=round(float(high_row[0]), 8),
        medium_rule=medium_rule,
        high_rule=high_rule,
        medium_f2=round(float(medium_row[4]), 8),
        medium_fpr=round(float(medium_row[3]), 8),
        high_precision=round(float(high_row[1]), 8),
        high_recall=round(float(high_row[2]), 8),
    )


def classify_transaction_risk(probability: float, thresholds: ThresholdArtifact) -> str:
    """Map calibrated fraud probability to the additive PR10 risk-band contract."""

    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise TransactionModelError("fraud probability must be finite and bounded")
    if not 0 <= thresholds.medium <= thresholds.high <= 1:
        raise TransactionModelError("transaction thresholds are invalid")
    if probability >= thresholds.high:
        return "high_risk"
    if probability >= thresholds.medium:
        return "medium_risk"
    return "low_risk"


def compatibility_risk_class(risk_band: str) -> str:
    """Project additive PR15 bands onto the fixed public three-class taxonomy."""

    mapping = {
        "low_risk": "GENUINE",
        "medium_risk": "SUSPICIOUS",
        "high_risk": "FRAUDULENT",
    }
    try:
        return mapping[risk_band]
    except KeyError as exc:
        raise TransactionModelError("unknown transaction risk band") from exc


def _runtime_inventory() -> dict[str, str]:
    versions = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "joblib": joblib.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit_learn": sklearn.__version__,
    }
    try:
        versions["xgboost"] = str(importlib.import_module("xgboost").__version__)
    except ImportError:
        versions["xgboost"] = "unavailable"
    return versions


def _model_card(report: Mapping[str, Any]) -> str:
    selection = cast(Mapping[str, Any], report["selection"])
    thresholds = cast(Mapping[str, Any], report["thresholds"])
    return "\n".join(
        [
            f"# Model Card — {report['model_version']}",
            "",
            "## Status and intended use",
            "",
            "- Component: `transaction_core` binary structured risk candidate",
            "- Status: exported research candidate; not activated and not final-test evaluated",
            "- Intended use: MoMo-FDVS research/demo risk evidence with required",
            "  transaction context",
            "- Prohibited use: provider verification, real-world fraud probability,",
            "  autonomous financial action",
            "- Data scope: synthetic PaySim/MoMTSim source-specific training only",
            "",
            "## Reproducibility",
            "",
            f"- Training commit: `{report['training_commit_sha']}`",
            f"- Dataset: `{report['dataset_id']}`",
            f"- Source SHA-256: `{report['source_sha256']}`",
            f"- Split manifest SHA-256: `{report['split_manifest_sha256']}`",
            f"- PR14 preprocessor SHA-256: `{report['preprocessor_sha256']}`",
            f"- Search configuration SHA-256: `{report['config_sha256']}`",
            f"- Selected family: `{selection['family']}`",
            f"- Selected seed: `{selection['seed']}`",
            "",
            "## Non-final selection evidence",
            "",
            f"- Tuning average precision: `{selection['tuning_average_precision']}`",
            f"- Calibration method: `{report['calibration']['selected_method']}`",
            f"- Medium threshold: `{thresholds['medium']}`",
            f"- High threshold: `{thresholds['high']}`",
            "- Locked test: sealed and not accessed; no final metric exists",
            "",
            "## Explainability",
            "",
            "User-facing reason categories are limited to unusual amount, high velocity,",
            "new recipient and sequence anomaly. They describe evidence patterns and do",
            "not claim causality or confirmed fraud.",
            "",
            "## Limitations",
            "",
            "Scores and calibration are source-specific synthetic research evidence and",
            "must be labelled `not_real_world_probability`. Domain shift, simulated class",
            "prevalence and missing real provider context prevent production claims. The",
            "locked final partition remains reserved for the one-time PR20 evaluation.",
            "",
        ]
    )


def predict_transaction_probability(
    bundle: Mapping[str, Any], frame: pd.DataFrame
) -> np.ndarray[Any, Any]:
    """Run verified bundle inference from the exact PR14 feature contract."""

    preprocessor = bundle.get("preprocessor")
    if not isinstance(preprocessor, FrozenPreprocessor):
        raise TransactionModelError("transaction bundle lacks its frozen preprocessor")
    model = bundle.get("model")
    calibrator = bundle.get("calibrator")
    if model is None or not isinstance(calibrator, BinaryCalibrator):
        raise TransactionModelError("transaction bundle is incomplete")
    transformed = apply_frozen_preprocessor(frame, preprocessor)
    return calibrator.transform(_probabilities(model, transformed))


def load_and_verify_transaction_artifact(path: Path, *, expected_sha256: str) -> Mapping[str, Any]:
    """Hash before loading a trusted PR15 joblib bundle and validate its contract."""

    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise TransactionModelError("expected transaction artifact SHA-256 is malformed")
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise TransactionModelError("transaction artifact hash mismatch")
    try:
        payload = joblib.load(path)
    except Exception as exc:
        raise TransactionModelError("unable to load verified transaction artifact") from exc
    if not isinstance(payload, dict):
        raise TransactionModelError("transaction artifact payload is invalid")
    if (
        payload.get("artifact_format") != ARTIFACT_FORMAT
        or payload.get("model_name") != MODEL_NAME
        or payload.get("model_contract_version") != MODEL_CONTRACT_VERSION
        or tuple(payload.get("feature_names", ())) != MODEL_FEATURES
        or payload.get("locked_test_accessed") is not False
        or payload.get("not_real_world_probability") is not True
    ):
        raise TransactionModelError("transaction artifact contract is incompatible")
    thresholds = payload.get("thresholds")
    if not isinstance(thresholds, ThresholdArtifact):
        raise TransactionModelError("transaction artifact thresholds are missing")
    classify_transaction_risk(thresholds.medium, thresholds)
    return cast(Mapping[str, Any], payload)


def evaluate_external_tuning_partition(
    artifact: Mapping[str, Any], *, external_dataset_root: Path
) -> dict[str, object]:
    """Evaluate one source-specific candidate on another source's non-final tuning rows."""

    external = verify_pr14_bundle(external_dataset_root)
    training_dataset_id = artifact.get("dataset_id")
    if training_dataset_id == external.dataset_id:
        raise TransactionModelError("external tuning evaluation requires a different source")
    try:
        features, labels = load_non_test_partition(
            dataset_root=external.root, partition="tuning", include_labels=True
        )
    except TransactionPipelineError as exc:
        raise TransactionModelError(str(exc)) from exc
    if labels is None or set(int(value) for value in labels.unique()) != {0, 1}:
        raise TransactionModelError("external tuning labels must contain both binary classes")
    probabilities = predict_transaction_probability(artifact, features)
    return {
        "schema_version": "transaction-core-external-tuning-v1",
        "training_dataset_id": training_dataset_id,
        "external_dataset_id": external.dataset_id,
        "external_source_sha256": external.source_sha256,
        "external_split_manifest_sha256": external.split_manifest_sha256,
        "partition": "tuning",
        "metrics": binary_metrics(labels.tolist(), probabilities.tolist()),
        "source_calibration_applied": True,
        "external_recalibration_performed": False,
        "interpretation": "domain_shift_research_only",
        "locked_test_accessed": False,
        "not_real_world_probability": True,
    }


def train_and_package_transaction_core(
    *,
    dataset_root: Path,
    output_dir: Path,
    model_version: str,
    training_commit_sha: str,
    notebook: str,
    dependency_lock_sha256: str,
    config: TransactionTrainingConfig | None = None,
    external_dataset_roots: Sequence[Path] = (),
) -> TransactionTrainingOutputs:
    """Run PR15 selection/calibration/export without reading the locked test."""

    run_started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if not SHA40.fullmatch(training_commit_sha):
        raise TransactionModelError("training commit must be 40 lowercase hexadecimal characters")
    if not SAFE_VERSION.fullmatch(model_version):
        raise TransactionModelError("transaction model version is unsafe")
    if not re.fullmatch(r"[0-9a-f]{64}", dependency_lock_sha256):
        raise TransactionModelError("dependency lock SHA-256 is malformed")
    active_config = default_training_config() if config is None else config
    _validate_config(active_config)
    bundle = verify_pr14_bundle(dataset_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_root = output_dir / "checkpoints"
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    train_x, train_y = load_pr15_partition(bundle, "train")
    tuning_x, tuning_y = load_pr15_partition(bundle, "tuning")
    calibration_x, calibration_y = load_pr15_partition(bundle, "calibration")
    candidate_records: list[dict[str, object]] = []
    search_seed = active_config.seeds[0]
    for candidate in active_config.candidates:
        _, result = _fit_or_resume_candidate(
            bundle=bundle,
            config=active_config,
            candidate=candidate,
            seed=search_seed,
            train_x=train_x,
            train_y=train_y,
            tuning_x=tuning_x,
            tuning_y=tuning_y,
            checkpoint_root=checkpoint_root,
        )
        candidate_records.append(result)
    non_dummy = [record for record in candidate_records if record["candidate"]["family"] != "dummy"]  # type: ignore[index]
    selectable = non_dummy or candidate_records
    best_search = max(
        selectable,
        key=lambda record: _candidate_rank(
            cast(Mapping[str, object], record["tuning_metrics"]),
            _as_float(record["recall_at_or_below_fpr_cap"]),
        ),
    )
    best_spec_payload = cast(Mapping[str, object], best_search["candidate"])
    best_spec = CandidateSpec(
        family=cast(str, best_spec_payload["family"]),
        parameters=cast(Mapping[str, object], best_spec_payload["parameters"]),
    )
    stability: list[dict[str, object]] = []
    stability_models: dict[int, Any] = {}
    for seed in active_config.seeds:
        model, result = _fit_or_resume_candidate(
            bundle=bundle,
            config=active_config,
            candidate=best_spec,
            seed=seed,
            train_x=train_x,
            train_y=train_y,
            tuning_x=tuning_x,
            tuning_y=tuning_y,
            checkpoint_root=checkpoint_root,
        )
        stability.append(result)
        stability_models[seed] = model
    selected_stability = max(
        stability,
        key=lambda record: _candidate_rank(
            cast(Mapping[str, object], record["tuning_metrics"]),
            _as_float(record["recall_at_or_below_fpr_cap"]),
        ),
    )
    selected_seed = _as_int(selected_stability["seed"])
    selected_model = stability_models[selected_seed]
    calibrator, threshold_scores, threshold_labels, calibration_report = calibrate_independently(
        selected_model,
        calibration_x,
        calibration_y,
        minimum_isotonic_positives=active_config.minimum_isotonic_positives,
    )
    thresholds = select_risk_thresholds(
        threshold_labels.tolist(),
        threshold_scores.tolist(),
        medium_fpr_cap=active_config.medium_fpr_cap,
        high_precision_target=active_config.high_precision_target,
    )
    artifact_payload: dict[str, object] = {
        "artifact_format": ARTIFACT_FORMAT,
        "model_name": MODEL_NAME,
        "model_contract_version": MODEL_CONTRACT_VERSION,
        "model_version": model_version,
        "dataset_id": bundle.dataset_id,
        "source_sha256": bundle.source_sha256,
        "split_manifest_sha256": bundle.split_manifest_sha256,
        "preprocessor_sha256": bundle.preprocessor.artifact_sha256,
        "config_sha256": active_config.config_sha256,
        "training_commit_sha": training_commit_sha,
        "selected_family": best_spec.family,
        "selected_parameters": dict(best_spec.parameters),
        "selected_seed": selected_seed,
        "feature_contract_version": FEATURE_CONTRACT_VERSION,
        "feature_names": MODEL_FEATURES,
        "preprocessor": bundle.preprocessor,
        "model": selected_model,
        "calibrator": calibrator,
        "thresholds": thresholds,
        "risk_band_compatibility": {
            "low_risk": "GENUINE",
            "medium_risk": "SUSPICIOUS",
            "high_risk": "FRAUDULENT",
        },
        "reason_categories": (
            "unusual_amount",
            "high_velocity",
            "new_recipient",
            "sequence_anomaly",
        ),
        "locked_test_accessed": False,
        "not_real_world_probability": True,
    }
    artifact_path = output_dir / f"{model_version}.joblib"
    artifact_sha256 = _dump_joblib_atomic(artifact_path, artifact_payload)
    verified = load_and_verify_transaction_artifact(artifact_path, expected_sha256=artifact_sha256)
    parity_count = min(active_config.parity_rows, len(calibration_x))
    parity_frame = calibration_x.iloc[:parity_count]
    before = calibrator.transform(_probabilities(selected_model, parity_frame))
    after = predict_transaction_probability(verified, parity_frame)
    if not np.allclose(before, after, rtol=1e-9, atol=1e-12):
        raise TransactionModelError("transaction artifact reload parity failed")
    prediction_digest = hashlib.sha256(after.astype(np.float64).tobytes()).hexdigest()
    external_evaluations: list[dict[str, object]] = []
    seen_external_ids: set[str] = set()
    for external_root in external_dataset_roots:
        evaluation = evaluate_external_tuning_partition(
            verified, external_dataset_root=external_root
        )
        external_id = cast(str, evaluation["external_dataset_id"])
        if external_id in seen_external_ids:
            raise TransactionModelError("external tuning dataset was supplied more than once")
        seen_external_ids.add(external_id)
        external_evaluations.append(evaluation)
    aps = [
        _as_float(cast(Mapping[str, object], record["tuning_metrics"])["average_precision"])
        for record in stability
    ]
    selection = {
        "family": best_spec.family,
        "parameters": dict(best_spec.parameters),
        "seed": selected_seed,
        "tuning_average_precision": cast(
            Mapping[str, object], selected_stability["tuning_metrics"]
        )["average_precision"],
        "tuning_recall_at_or_below_fpr_cap": selected_stability["recall_at_or_below_fpr_cap"],
        "three_seed_average_precision_mean": round(statistics.fmean(aps), 8),
        "three_seed_average_precision_stddev": round(statistics.pstdev(aps), 8),
    }
    report: dict[str, Any] = {
        "schema_version": REPORT_VERSION,
        "model_name": MODEL_NAME,
        "model_version": model_version,
        "dataset_id": bundle.dataset_id,
        "source_sha256": bundle.source_sha256,
        "build_report_sha256": bundle.build_report_sha256,
        "split_manifest_sha256": bundle.split_manifest_sha256,
        "preprocessor_sha256": bundle.preprocessor.artifact_sha256,
        "config_sha256": active_config.config_sha256,
        "training_commit_sha": training_commit_sha,
        "runtime_inventory": _runtime_inventory(),
        "candidates": candidate_records,
        "stability": stability,
        "selection": selection,
        "calibration": calibration_report,
        "thresholds": thresholds.safe_dict(),
        "external_tuning_evaluations": external_evaluations,
        "artifact": {
            "format": ARTIFACT_FORMAT,
            "sha256": artifact_sha256,
            "reload_parity_rows": parity_count,
            "reload_prediction_digest": prediction_digest,
        },
        "explainability_reason_categories": [
            "unusual_amount",
            "high_velocity",
            "new_recipient",
            "sequence_anomaly",
        ],
        "locked_test_sealed": True,
        "locked_test_accessed_for_decisions": False,
        "full_training_executed": True,
        "final_evaluation_executed": False,
        "not_real_world_probability": True,
        "promotable": False,
        "limitations": [
            "Training and calibration use synthetic source-specific transaction distributions.",
            "Calibration is not a real-world Ghanaian fraud probability.",
            "The locked final partition remains unopened until logical PR20.",
        ],
    }
    report_path = output_dir / "training-report.json"
    _write_json_atomic(report_path, report)
    model_card_path = output_dir / "MODEL_CARD.md"
    model_card_path.write_text(_model_card(report), encoding="utf-8", newline="\n")
    registry_payload = {
        "model_name": MODEL_NAME,
        "model_version": model_version,
        "artifact_format": ARTIFACT_FORMAT,
        "artifact_sha256": artifact_sha256,
        "feature_contract_version": FEATURE_CONTRACT_VERSION,
        "source_dataset": bundle.dataset_id,
        "source_sha256": bundle.source_sha256,
        "split_manifest_sha256": bundle.split_manifest_sha256,
        "threshold_schema_version": THRESHOLD_VERSION,
        "status": "EXPERIMENTAL_NOT_FINAL_EVALUATED",
        "activation_allowed": False,
    }
    registry_payload_path = output_dir / "registry-payload.json"
    _write_json_atomic(registry_payload_path, registry_payload)
    run_id = (
        f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}_transaction-core_"
        f"{training_commit_sha[:8]}_seed{selected_seed}"
    )
    run_completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    manifest_artifacts = [
        {
            "name": name,
            "path": path.name,
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for name, path in (
            ("transaction_core", artifact_path),
            ("training_report", report_path),
            ("model_card", model_card_path),
            ("registry_payload", registry_payload_path),
        )
    ]
    manifest_checkpoints = [
        {
            "checkpoint_id": path.name,
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(checkpoint_root.iterdir())
        if path.is_file()
    ]
    run_manifest = {
        "schema_version": "colab-run-manifest-v1",
        "foundation_version": "colab-foundation-v1",
        "run_id": run_id,
        "profile": "full",
        "status": "completed",
        "started_at": run_started_at,
        "completed_at": run_completed_at,
        "git": {"commit": training_commit_sha, "dirty": False},
        "notebook": notebook,
        "runtime_inventory": _runtime_inventory(),
        "seed": selected_seed,
        "dependency_lock": {
            "path": "ml/requirements-training.lock",
            "sha256": dependency_lock_sha256,
        },
        "dataset_manifest_sha256": bundle.build_report_sha256,
        "split_manifest_sha256": bundle.split_manifest_sha256,
        "config_sha256": active_config.config_sha256,
        "feature_schema_versions": [FEATURE_CONTRACT_VERSION, MODEL_CONTRACT_VERSION],
        "artifacts": manifest_artifacts,
        "checkpoints": manifest_checkpoints,
        "sessions": [
            {
                "session_index": 0,
                "started_at": run_started_at,
                "completed_at": run_completed_at,
                "resumed_from_checkpoint_sha256": None,
                "outcome": "completed",
            }
        ],
        "limitations": report["limitations"],
        "acquisition_executed": False,
        "full_training_executed": True,
        "promotable": False,
    }
    run_manifest_path = output_dir / "run-manifest.json"
    _write_json_atomic(run_manifest_path, run_manifest)
    return TransactionTrainingOutputs(
        artifact_path=artifact_path,
        artifact_sha256=artifact_sha256,
        report_path=report_path,
        model_card_path=model_card_path,
        registry_payload_path=registry_payload_path,
        run_manifest_path=run_manifest_path,
        report=report,
    )


def runtime_fingerprint() -> dict[str, str]:
    """Expose the PR15 inference/runtime fingerprint without fitting."""

    return _runtime_inventory()
