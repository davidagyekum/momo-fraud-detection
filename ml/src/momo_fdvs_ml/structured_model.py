"""Deterministic structured Random Forest training, evaluation and packaging."""

from __future__ import annotations

import json
import math
import platform
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, cast

import joblib
import numpy as np
import pandas as pd
import sklearn
from PIL import Image, ImageDraw, ImageFont
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from momo_fdvs_ml.feature_schema import (
    CATEGORICAL_FEATURE_NAMES,
    FEATURE_NAMES,
    NUMERIC_FEATURE_NAMES,
    RISK_CLASSES,
    RISK_SCALAR_VERSION,
    STRUCTURED_FEATURE_SCHEMA_HASH,
    STRUCTURED_FEATURE_SCHEMA_VERSION,
    calculate_risk_scalar,
    classify_risk_scalar,
    feature_schema_hash,
    feature_schema_payload,
    validate_feature_row,
)
from momo_fdvs_ml.manifest import sha256_file
from momo_fdvs_ml.structured_dataset import StructuredDataset

ARTIFACT_FORMAT: Final = "momo-fdvs-trusted-joblib-v1"
MODEL_NAME: Final = "momo-fdvs-structured-risk"
PREPROCESSING_VERSION: Final = "structured-column-transformer-v1"
RANDOM_SEED: Final = 20260811
DEFAULT_ESTIMATORS: Final = 300
MIN_ACCEPTABLE_MACRO_F1: Final = 0.85
SHA_PATTERN: Final = re.compile(r"[0-9a-f]{40}")


class StructuredModelError(RuntimeError):
    """Raised when training, packaging or inference evidence is invalid."""


@dataclass(frozen=True)
class Thresholds:
    """Validation-selected ordered thresholds for the scalar ML component."""

    suspicious: float
    fraudulent: float
    validation_macro_f1: float
    validation_fraudulent_recall: float

    def as_dict(self) -> dict[str, float]:
        return {
            "suspicious": self.suspicious,
            "fraudulent": self.fraudulent,
            "validation_macro_f1": self.validation_macro_f1,
            "validation_fraudulent_recall": self.validation_fraudulent_recall,
        }


@dataclass(frozen=True)
class TrainingOutputs:
    """Safe report paths plus the ignored trusted artifact path."""

    artifact_path: Path
    artifact_sha256: str
    report_path: Path
    model_card_path: Path
    registry_payload_path: Path
    confusion_matrix_path: Path
    report: Mapping[str, Any]


def build_pipeline(
    *, random_seed: int = RANDOM_SEED, n_estimators: int = DEFAULT_ESTIMATORS
) -> Pipeline:
    """Build the exact preprocessing/model graph fit only on training rows."""

    numeric = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
        ]
    )
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )
    preprocess = ColumnTransformer(
        transformers=[
            ("numeric", numeric, list(NUMERIC_FEATURE_NAMES)),
            ("categorical", categorical, list(CATEGORICAL_FEATURE_NAMES)),
        ],
        remainder="drop",
        verbose_feature_names_out=True,
    )
    classifier = RandomForestClassifier(
        n_estimators=n_estimators,
        class_weight="balanced",
        random_state=random_seed,
        n_jobs=1,
        min_samples_leaf=1,
        max_features="sqrt",
    )
    return Pipeline(steps=[("preprocess", preprocess), ("classifier", classifier)])


def _probability_rows(pipeline: Pipeline, frame: pd.DataFrame) -> tuple[dict[str, float], ...]:
    raw = cast(np.ndarray, pipeline.predict_proba(frame))
    classes = tuple(str(value) for value in pipeline.classes_)
    if set(classes) != set(RISK_CLASSES):
        raise StructuredModelError("trained classifier does not expose all three risk classes")
    rows: list[dict[str, float]] = []
    for vector in raw:
        probabilities = {label: float(vector[classes.index(label)]) for label in RISK_CLASSES}
        total = sum(probabilities.values())
        if not math.isfinite(total) or total <= 0:
            raise StructuredModelError("classifier produced invalid probability mass")
        normalised = {label: value / total for label, value in probabilities.items()}
        calculate_risk_scalar(normalised)
        rows.append(normalised)
    return tuple(rows)


def select_thresholds(
    labels: Sequence[str], probabilities: Sequence[Mapping[str, float]]
) -> Thresholds:
    """Select thresholds on validation data only with fraud-recall tie breaking."""

    if len(labels) != len(probabilities) or not labels:
        raise StructuredModelError("validation labels and probabilities must be non-empty")
    scalars = [calculate_risk_scalar(row) for row in probabilities]
    best: tuple[float, float, float, float] | None = None
    for suspicious_index in range(5, 61, 5):
        suspicious = suspicious_index / 100
        for fraudulent_index in range(max(40, suspicious_index + 5), 96, 5):
            fraudulent = fraudulent_index / 100
            predicted = [
                classify_risk_scalar(
                    scalar,
                    suspicious_threshold=suspicious,
                    fraudulent_threshold=fraudulent,
                )
                for scalar in scalars
            ]
            macro_f1 = float(
                f1_score(labels, predicted, labels=list(RISK_CLASSES), average="macro")
            )
            _, recalls, _, _ = precision_recall_fscore_support(
                labels,
                predicted,
                labels=list(RISK_CLASSES),
                zero_division=0,
            )
            fraud_recall = float(recalls[RISK_CLASSES.index("FRAUDULENT")])
            candidate = (macro_f1, fraud_recall, -fraudulent, -suspicious)
            if best is None or candidate > best:
                best = candidate
    if best is None:
        raise StructuredModelError("unable to select validation thresholds")
    return Thresholds(
        suspicious=round(-best[3], 6),
        fraudulent=round(-best[2], 6),
        validation_macro_f1=round(best[0], 6),
        validation_fraudulent_recall=round(best[1], 6),
    )


def _calibration_diagnostics(
    labels: Sequence[str], probabilities: Sequence[Mapping[str, float]], *, bins: int = 5
) -> dict[str, object]:
    label_indexes = {label: index for index, label in enumerate(RISK_CLASSES)}
    matrix = np.asarray(
        [[row[label] for label in RISK_CLASSES] for row in probabilities], dtype=float
    )
    one_hot = np.zeros_like(matrix)
    for index, label in enumerate(labels):
        one_hot[index, label_indexes[label]] = 1.0
    multiclass_brier = float(np.mean(np.sum((matrix - one_hot) ** 2, axis=1)))
    confidences = matrix.max(axis=1)
    predictions = matrix.argmax(axis=1)
    truths = np.asarray([label_indexes[label] for label in labels], dtype=int)
    edges = np.linspace(0.0, 1.0, bins + 1)
    rows: list[dict[str, float | int]] = []
    ece = 0.0
    for index in range(bins):
        lower = edges[index]
        upper = edges[index + 1]
        selected = (confidences >= lower) & (
            confidences <= upper if index == bins - 1 else confidences < upper
        )
        count = int(selected.sum())
        if count == 0:
            continue
        mean_confidence = float(confidences[selected].mean())
        accuracy = float((predictions[selected] == truths[selected]).mean())
        ece += (count / len(labels)) * abs(accuracy - mean_confidence)
        rows.append(
            {
                "lower": round(float(lower), 4),
                "upper": round(float(upper), 4),
                "count": count,
                "mean_confidence": round(mean_confidence, 6),
                "accuracy": round(accuracy, 6),
            }
        )
    return {
        "multiclass_brier": round(multiclass_brier, 6),
        "expected_calibration_error": round(float(ece), 6),
        "bins": rows,
        "calibration_applied": False,
        "calibration_reason": (
            "No calibrator was fit: the controlled validation partition has only one "
            "source group and three rows; fitting calibration would overstate evidence."
        ),
    }


def evaluate_partition(
    labels: Sequence[str],
    probabilities: Sequence[Mapping[str, float]],
    *,
    thresholds: Thresholds,
    sample_ids: Sequence[str],
    groups: Sequence[str],
) -> dict[str, object]:
    """Evaluate one untouched partition and preserve sample/group provenance."""

    if not (len(labels) == len(probabilities) == len(sample_ids) == len(groups)):
        raise StructuredModelError("evaluation arrays must have equal length")
    scalars = [calculate_risk_scalar(row) for row in probabilities]
    predicted = [
        classify_risk_scalar(
            scalar,
            suspicious_threshold=thresholds.suspicious,
            fraudulent_threshold=thresholds.fraudulent,
        )
        for scalar in scalars
    ]
    matrix = confusion_matrix(labels, predicted, labels=list(RISK_CLASSES)).tolist()
    report = classification_report(
        labels,
        predicted,
        labels=list(RISK_CLASSES),
        output_dict=True,
        zero_division=0,
    )
    per_class = {
        label: {
            key: round(float(report[label][key]), 6)
            for key in ("precision", "recall", "f1-score", "support")
        }
        for label in RISK_CLASSES
    }
    return {
        "sample_count": len(labels),
        "source_group_count": len(set(groups)),
        "sample_ids": list(sample_ids),
        "source_groups": sorted(set(groups)),
        "labels": list(labels),
        "predicted": predicted,
        "probabilities": [
            {label: round(float(row[label]), 8) for label in RISK_CLASSES} for row in probabilities
        ],
        "risk_scalars": [round(value, 8) for value in scalars],
        "confusion_matrix_labels": list(RISK_CLASSES),
        "confusion_matrix": matrix,
        "per_class": per_class,
        "macro_f1": round(
            float(f1_score(labels, predicted, labels=list(RISK_CLASSES), average="macro")),
            6,
        ),
        "balanced_accuracy": round(float(balanced_accuracy_score(labels, predicted)), 6),
        "calibration": _calibration_diagnostics(labels, probabilities),
    }


def _framework_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "joblib": joblib.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit_learn": sklearn.__version__,
    }


def _write_confusion_matrix(path: Path, matrix: Sequence[Sequence[int]]) -> None:
    size = 720
    margin = 160
    cell = 160
    image = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=24)
    small = ImageFont.load_default(size=18)
    draw.text((170, 28), "Held-out controlled test confusion matrix", fill="#173f36", font=font)
    for index, label in enumerate(RISK_CLASSES):
        draw.text((margin + index * cell + 25, 100), label[:5], fill="#333333", font=small)
        draw.text((20, margin + index * cell + 65), label[:8], fill="#333333", font=small)
    maximum = max(1, max(max(row) for row in matrix))
    for row_index, row in enumerate(matrix):
        for column_index, value in enumerate(row):
            ratio = value / maximum
            shade = int(245 - ratio * 130)
            box = (
                margin + column_index * cell,
                margin + row_index * cell,
                margin + (column_index + 1) * cell,
                margin + (row_index + 1) * cell,
            )
            draw.rectangle(box, fill=(shade, 226, shade), outline="#315e52", width=2)
            draw.text(
                (box[0] + 70, box[1] + 60),
                str(value),
                fill="#111111",
                font=font,
            )
    draw.text((300, 660), "Predicted", fill="#333333", font=small)
    draw.text((20, 620), "Actual", fill="#333333", font=small)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=False, compress_level=9)


def _model_card(report: Mapping[str, Any]) -> str:
    test = cast(Mapping[str, Any], report["held_out_test"])
    thresholds = cast(Mapping[str, Any], report["thresholds"])
    artifact = cast(Mapping[str, Any], report["artifact"])
    status = "READY" if report["acceptance_passed"] else "FAILED"
    lines = [
        f"# Model Card — {report['model_version']}",
        "",
        "## Status and intended use",
        "",
        "- Model type: structured Random Forest baseline",
        f"- Status after training: {status}; never auto-activated",
        "- Intended use: controlled MoMo-FDVS prototype evidence before human review",
        "- Prohibited claims: provider-wide accuracy, production readiness, fraud proof",
        "  or autonomous consequential decisions",
        "- Dataset scope: controlled/synthetic only; no real customer or provider data",
        "",
        "## Reproducibility",
        "",
        f"- Training commit: `{report['training_commit_sha']}`",
        f"- Random seed: `{report['random_seed']}`",
        f"- Feature schema: `{report['feature_schema_version']}`",
        f"- Feature schema SHA-256: `{report['feature_schema_hash']}`",
        f"- P10 manifest SHA-256: `{report['dataset_manifest_hash']}`",
        f"- P10 split SHA-256: `{report['split_hash']}`",
        f"- Structured dataset SHA-256: `{report['structured_dataset_hash']}`",
        f"- Artifact SHA-256: `{artifact['sha256']}`",
        "",
        "## Held-out controlled results",
        "",
        f"- Test source groups: `{test['source_group_count']}`",
        f"- Test samples: `{test['sample_count']}`",
        f"- Macro F1: `{test['macro_f1']}`",
        f"- Balanced accuracy: `{test['balanced_accuracy']}`",
        f"- Suspicious threshold (validation only): `{thresholds['suspicious']}`",
        f"- Fraudulent threshold (validation only): `{thresholds['fraudulent']}`",
        f"- Confusion matrix labels: `{test['confusion_matrix_labels']}`",
        f"- Confusion matrix: `{test['confusion_matrix']}`",
        "",
        "## Limitations",
        "",
        "The held-out partition contains one controlled source group and one row per class.",
        "Strong results demonstrate deterministic pipeline behaviour only. They do not",
        "estimate generalisation to real receipts, provider layouts, user populations or",
        "naturally occurring fraud. The probability vector is uncalibrated because the",
        "validation partition is too small to fit a defensible calibrator. Human review and",
        "authorised provider confirmation remain necessary for consequential cases.",
    ]
    return "\n".join(lines) + "\n"


def train_and_package(
    *,
    dataset: StructuredDataset,
    output_dir: Path,
    model_version: str,
    training_commit_sha: str,
    random_seed: int = RANDOM_SEED,
) -> TrainingOutputs:
    """Fit on train, tune thresholds on validation, evaluate test once, and package."""

    if not SHA_PATTERN.fullmatch(training_commit_sha):
        raise StructuredModelError(
            "training_commit_sha must be exactly 40 lowercase hex characters"
        )
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,99}", model_version):
        raise StructuredModelError("model_version must be a safe lowercase identifier")
    train_x, train_y, train_groups, train_ids = dataset.partition("train")
    validation_x, validation_y, validation_groups, validation_ids = dataset.partition("validation")
    test_x, test_y, test_groups, test_ids = dataset.partition("test")
    partitions = {
        "train": set(train_groups),
        "validation": set(validation_groups),
        "test": set(test_groups),
    }
    if (
        partitions["train"] & partitions["validation"]
        or partitions["train"] & partitions["test"]
        or partitions["validation"] & partitions["test"]
    ):
        raise StructuredModelError("source group leakage exists across fit/evaluation partitions")

    pipeline = build_pipeline(random_seed=random_seed)
    pipeline.fit(train_x, train_y)
    validation_probabilities = _probability_rows(pipeline, validation_x)
    thresholds = select_thresholds(list(validation_y), validation_probabilities)
    validation_metrics = evaluate_partition(
        list(validation_y),
        validation_probabilities,
        thresholds=thresholds,
        sample_ids=validation_ids,
        groups=validation_groups,
    )
    test_probabilities = _probability_rows(pipeline, test_x)
    test_metrics = evaluate_partition(
        list(test_y),
        test_probabilities,
        thresholds=thresholds,
        sample_ids=test_ids,
        groups=test_groups,
    )
    acceptance_passed = bool(
        cast(float, test_metrics["macro_f1"]) >= MIN_ACCEPTABLE_MACRO_F1
        and cast(float, test_metrics["balanced_accuracy"]) >= 0.80
        and cast(int, test_metrics["source_group_count"]) >= 1
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / f"{model_version}.joblib"
    bundle = {
        "artifact_format": ARTIFACT_FORMAT,
        "model_name": MODEL_NAME,
        "model_version": model_version,
        "pipeline": pipeline,
        "classes": list(RISK_CLASSES),
        "feature_names": list(FEATURE_NAMES),
        "feature_schema": feature_schema_payload(),
        "feature_schema_hash": STRUCTURED_FEATURE_SCHEMA_HASH,
        "feature_schema_version": STRUCTURED_FEATURE_SCHEMA_VERSION,
        "preprocessing_version": PREPROCESSING_VERSION,
        "risk_scalar_version": RISK_SCALAR_VERSION,
        "thresholds": {
            "suspicious": thresholds.suspicious,
            "fraudulent": thresholds.fraudulent,
        },
        "random_seed": random_seed,
        "training_commit_sha": training_commit_sha,
        "dataset_manifest_hash": dataset.source_manifest_hash,
        "split_hash": dataset.source_split_hash,
        "structured_dataset_hash": dataset.dataset_hash,
        "framework_versions": _framework_versions(),
    }
    joblib.dump(bundle, artifact_path, compress=3, protocol=5)
    artifact_sha = sha256_file(artifact_path)
    report: dict[str, Any] = {
        "report_version": "structured-model-evaluation-v1",
        "model_name": MODEL_NAME,
        "model_version": model_version,
        "training_commit_sha": training_commit_sha,
        "random_seed": random_seed,
        "feature_schema_version": STRUCTURED_FEATURE_SCHEMA_VERSION,
        "feature_schema_hash": STRUCTURED_FEATURE_SCHEMA_HASH,
        "preprocessing_version": PREPROCESSING_VERSION,
        "risk_scalar_version": RISK_SCALAR_VERSION,
        "dataset_scope": "controlled_synthetic_only",
        "dataset_manifest_hash": dataset.source_manifest_hash,
        "split_hash": dataset.source_split_hash,
        "structured_dataset_hash": dataset.dataset_hash,
        "partition_groups": {split: sorted(groups) for split, groups in partitions.items()},
        "train_sample_ids": list(train_ids),
        "thresholds": thresholds.as_dict(),
        "validation": validation_metrics,
        "held_out_test": test_metrics,
        "acceptance_thresholds": {
            "macro_f1_minimum": MIN_ACCEPTABLE_MACRO_F1,
            "balanced_accuracy_minimum": 0.80,
        },
        "acceptance_passed": acceptance_passed,
        "framework_versions": _framework_versions(),
        "artifact": {
            "filename": artifact_path.name,
            "sha256": artifact_sha,
            "committed_to_git": False,
        },
        "limitations": [
            "Controlled/synthetic data only; no provider-wide or production claim is allowed.",
            "The held-out test partition has one source group and three rows.",
            "No probability calibrator was fit because the validation partition is too small.",
            "The artifact must be hash-verified before trusted joblib deserialisation.",
        ],
    }
    report_path = output_dir / "structured_evaluation_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    model_card_path = output_dir / "STRUCTURED_MODEL_CARD.md"
    model_card_path.write_text(_model_card(report), encoding="utf-8", newline="\n")
    registry_payload = {
        "model_type": "STRUCTURED",
        "name": MODEL_NAME,
        "version": model_version,
        "artifact_uri": f"private://structured/{artifact_path.name}",
        "artifact_sha256": artifact_sha,
        "input_schema_hash": STRUCTURED_FEATURE_SCHEMA_HASH,
        "preprocessing_version": PREPROCESSING_VERSION,
        "framework_versions": _framework_versions(),
        "metrics": {
            "scope": "controlled_synthetic_only",
            "macro_f1": test_metrics["macro_f1"],
            "balanced_accuracy": test_metrics["balanced_accuracy"],
            "thresholds": thresholds.as_dict(),
            "acceptance_passed": acceptance_passed,
        },
        "dataset_manifest_hash": dataset.source_manifest_hash,
        "split_hash": dataset.source_split_hash,
        "training_commit_sha": training_commit_sha,
        "model_card_key": "docs/models/STRUCTURED_MODEL_CARD_CONTROLLED_V1.md",
    }
    registry_payload_path = output_dir / "structured_registry_payload.json"
    registry_payload_path.write_text(
        json.dumps(registry_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    confusion_matrix_path = output_dir / "structured_confusion_matrix.png"
    _write_confusion_matrix(
        confusion_matrix_path,
        cast(Sequence[Sequence[int]], test_metrics["confusion_matrix"]),
    )
    return TrainingOutputs(
        artifact_path=artifact_path,
        artifact_sha256=artifact_sha,
        report_path=report_path,
        model_card_path=model_card_path,
        registry_payload_path=registry_payload_path,
        confusion_matrix_path=confusion_matrix_path,
        report=report,
    )


def load_and_verify_artifact(
    path: Path, *, expected_sha256: str, expected_schema_hash: str
) -> dict[str, Any]:
    """Hash an explicitly trusted artifact before joblib deserialisation."""

    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise StructuredModelError("expected artifact hash is invalid")
    if sha256_file(path) != expected_sha256:
        raise StructuredModelError("structured artifact SHA-256 mismatch")
    bundle = joblib.load(path)
    if not isinstance(bundle, dict) or bundle.get("artifact_format") != ARTIFACT_FORMAT:
        raise StructuredModelError("structured artifact format is unsupported")
    schema = bundle.get("feature_schema")
    if not isinstance(schema, dict):
        raise StructuredModelError("structured artifact schema is missing")
    actual_schema_hash = feature_schema_hash(schema)
    if actual_schema_hash != expected_schema_hash or actual_schema_hash != bundle.get(
        "feature_schema_hash"
    ):
        raise StructuredModelError("structured artifact feature schema hash mismatch")
    if bundle.get("classes") != list(RISK_CLASSES):
        raise StructuredModelError("structured artifact class ordering is invalid")
    if bundle.get("feature_names") != list(FEATURE_NAMES):
        raise StructuredModelError("structured artifact feature ordering is invalid")
    return cast(dict[str, Any], bundle)


def predict_with_bundle(
    bundle: Mapping[str, Any], feature_row: Mapping[str, object]
) -> dict[str, object]:
    """Run deterministic inference with a previously hash-verified bundle."""

    normalised = validate_feature_row(feature_row)
    pipeline = bundle.get("pipeline")
    if not isinstance(pipeline, Pipeline):
        raise StructuredModelError("structured artifact pipeline is invalid")
    frame = pd.DataFrame([normalised], columns=list(FEATURE_NAMES))
    probabilities = _probability_rows(pipeline, frame)[0]
    risk_scalar = calculate_risk_scalar(probabilities)
    thresholds = bundle.get("thresholds")
    if not isinstance(thresholds, dict):
        raise StructuredModelError("structured artifact thresholds are invalid")
    predicted = classify_risk_scalar(
        risk_scalar,
        suspicious_threshold=float(thresholds["suspicious"]),
        fraudulent_threshold=float(thresholds["fraudulent"]),
    )
    return {
        "predicted_class": predicted,
        "probabilities": {label: round(float(probabilities[label]), 8) for label in RISK_CLASSES},
        "risk_scalar": round(risk_scalar, 8),
        "risk_scalar_version": RISK_SCALAR_VERSION,
        "model_name": bundle["model_name"],
        "model_version": bundle["model_version"],
        "feature_schema_version": bundle["feature_schema_version"],
        "feature_schema_hash": bundle["feature_schema_hash"],
    }


def runtime_fingerprint() -> dict[str, str]:
    """Expose safe runtime evidence for Colab reports and diagnostics."""

    versions = _framework_versions()
    versions["platform"] = platform.platform()
    versions["byteorder"] = sys.byteorder
    return versions
