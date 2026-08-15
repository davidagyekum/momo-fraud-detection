"""TensorFlow/Keras controlled-tamper training, evaluation and artifact packaging."""

from __future__ import annotations

import contextlib
import importlib
import json
import math
import platform
import re
import statistics
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Final, cast

import numpy as np
from PIL import Image, ImageDraw
from sklearn.metrics import (
    auc,
    classification_report,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
)

from momo_fdvs_ml.image_schema import (
    IMAGE_CLASSES,
    IMAGE_INPUT_CHANNELS,
    IMAGE_INPUT_HEIGHT,
    IMAGE_INPUT_WIDTH,
    IMAGE_MODEL_NAME,
    IMAGE_PREPROCESSING_SCHEMA_HASH,
    IMAGE_PREPROCESSING_VERSION,
    IMAGE_RANDOM_SEED,
    ImageDatasetError,
    ImageSample,
    governed_image_samples,
    preprocess_image_path,
)
from momo_fdvs_ml.manifest import load_manifest, sha256_file

IMAGE_ARTIFACT_FORMAT: Final = "keras-v3"
IMAGE_ARCHITECTURE_VERSION: Final = "mobilenetv3small-controlled-head-v1"
IMAGE_REPORT_VERSION: Final = "image-model-evaluation-v1"
DEFAULT_THRESHOLD: Final = 0.5
MIN_ACCEPTABLE_MACRO_F1: Final = 0.85
SHA_PATTERN: Final = re.compile(r"[0-9a-f]{40}")


class ImageModelError(RuntimeError):
    """Raised when image-model training or evidence is invalid."""


@dataclass(frozen=True)
class ImageThreshold:
    value: float
    validation_macro_f1: float
    validation_tampered_recall: float

    def as_dict(self) -> dict[str, float]:
        return {
            "value": self.value,
            "validation_macro_f1": self.validation_macro_f1,
            "validation_tampered_recall": self.validation_tampered_recall,
        }


@dataclass(frozen=True)
class ImageTrainingOutputs:
    artifact_path: Path
    artifact_sha256: str
    report_path: Path
    model_card_path: Path
    registry_payload_path: Path
    confusion_matrix_path: Path
    report: Mapping[str, Any]


def _tensorflow() -> Any:
    try:
        return importlib.import_module("tensorflow")
    except ImportError as exc:
        raise ImageModelError(
            "TensorFlow 2.21.0 is required; reportable training must run in Google Colab"
        ) from exc


def runtime_fingerprint() -> dict[str, str]:
    tf = _tensorflow()
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "tensorflow": str(tf.__version__),
        "numpy": np.__version__,
        "pillow": metadata.version("Pillow"),
        "scikit_learn": metadata.version("scikit-learn"),
    }


def training_policy() -> dict[str, object]:
    return {
        "architecture": "MobileNetV3Small",
        "architecture_version": IMAGE_ARCHITECTURE_VERSION,
        "backbone_weights": "imagenet",
        "head": ["GlobalAveragePooling2D", "Dropout(0.2)", "Dense(1,sigmoid)"],
        "loss": "binary_crossentropy",
        "checkpoint_monitor": "val_pr_auc",
        "checkpoint_mode": "max",
        "head_stage": {"epochs": 20, "learning_rate": 0.001, "backbone_frozen": True},
        "fine_tune_stage": {
            "epochs": 10,
            "learning_rate": 0.00001,
            "unfreeze_last_backbone_layers": 20,
        },
        "early_stopping_patience": 5,
        "threshold_partition": "validation",
        "test_policy": "evaluate_once_after_checkpoint_selection",
        "class_weight_source": "training_partition_only",
    }


def class_weights(labels: Sequence[int]) -> dict[int, float]:
    """Calculate balanced class weights from training labels only."""

    counts = Counter(labels)
    if set(counts) != {0, 1}:
        raise ImageModelError("training labels must contain both image classes")
    total = len(labels)
    return {index: total / (2.0 * counts[index]) for index in (0, 1)}


def _binary_f1(labels: np.ndarray, predicted: np.ndarray, positive: int) -> float:
    true_positive = int(((labels == positive) & (predicted == positive)).sum())
    false_positive = int(((labels != positive) & (predicted == positive)).sum())
    false_negative = int(((labels == positive) & (predicted != positive)).sum())
    denominator = 2 * true_positive + false_positive + false_negative
    return 0.0 if denominator == 0 else (2 * true_positive) / denominator


def select_image_threshold(labels: Sequence[int], probabilities: Sequence[float]) -> ImageThreshold:
    """Select the probability threshold using validation data only."""

    truth = np.asarray(labels, dtype=int)
    scores = np.asarray(probabilities, dtype=float)
    if truth.shape != scores.shape or truth.size == 0 or set(truth.tolist()) != {0, 1}:
        raise ImageModelError("validation labels/probabilities must contain both classes")
    if not np.isfinite(scores).all() or bool(((scores < 0) | (scores > 1)).any()):
        raise ImageModelError("validation probabilities must be finite and within zero to one")
    best: tuple[float, float, float] | None = None
    for threshold_index in range(5, 96, 5):
        threshold = threshold_index / 100
        predicted = (scores >= threshold).astype(int)
        original_f1 = _binary_f1(truth, predicted, 0)
        tampered_f1 = _binary_f1(truth, predicted, 1)
        tampered_true = int((truth == 1).sum())
        tampered_recall = float(((truth == 1) & (predicted == 1)).sum() / tampered_true)
        candidate = ((original_f1 + tampered_f1) / 2.0, tampered_recall, -threshold)
        if best is None or candidate > best:
            best = candidate
    if best is None:
        raise ImageModelError("unable to select an image threshold")
    return ImageThreshold(
        value=round(-best[2], 6),
        validation_macro_f1=round(best[0], 6),
        validation_tampered_recall=round(best[1], 6),
    )


def _calibration(labels: np.ndarray, scores: np.ndarray, *, bins: int = 5) -> dict[str, object]:
    brier = float(np.mean((scores - labels) ** 2))
    edges = np.linspace(0.0, 1.0, bins + 1)
    rows: list[dict[str, float | int]] = []
    ece = 0.0
    for index in range(bins):
        lower = edges[index]
        upper = edges[index + 1]
        selected = (scores >= lower) & (scores <= upper if index == bins - 1 else scores < upper)
        count = int(selected.sum())
        if count == 0:
            continue
        mean_score = float(scores[selected].mean())
        observed = float(labels[selected].mean())
        ece += count / len(labels) * abs(observed - mean_score)
        rows.append(
            {
                "lower": round(float(lower), 4),
                "upper": round(float(upper), 4),
                "count": count,
                "mean_probability": round(mean_score, 6),
                "observed_tampered_rate": round(observed, 6),
            }
        )
    return {
        "brier": round(brier, 6),
        "expected_calibration_error": round(ece, 6),
        "bins": rows,
        "calibration_applied": False,
        "calibration_reason": (
            "No calibrator is fit for the six-group controlled corpus; "
            "the diagnostic is descriptive."
        ),
    }


def evaluate_binary_partition(
    labels: Sequence[int],
    probabilities: Sequence[float],
    *,
    threshold: ImageThreshold,
    samples: Sequence[ImageSample],
) -> dict[str, object]:
    """Generate honest binary metrics with sample and source-group provenance."""

    truth = np.asarray(labels, dtype=int)
    scores = np.asarray(probabilities, dtype=float)
    if len(samples) != len(truth) or truth.shape != scores.shape or truth.size == 0:
        raise ImageModelError("evaluation arrays must be non-empty and have equal length")
    if not np.isfinite(scores).all() or bool(((scores < 0) | (scores > 1)).any()):
        raise ImageModelError("evaluation probabilities must be finite and within zero to one")
    predicted = (scores >= threshold.value).astype(int)
    target_names = list(IMAGE_CLASSES)
    report = classification_report(
        truth,
        predicted,
        labels=[0, 1],
        target_names=target_names,
        output_dict=True,
        zero_division=0,
    )
    precision, recall, _ = precision_recall_curve(truth, scores)
    per_class = {
        label: {
            metric: round(float(report[label][metric]), 6)
            for metric in ("precision", "recall", "f1-score", "support")
        }
        for label in IMAGE_CLASSES
    }
    roc_auc = float(roc_auc_score(truth, scores)) if set(truth.tolist()) == {0, 1} else None
    return {
        "sample_count": len(samples),
        "source_group_count": len({sample.source_group_id for sample in samples}),
        "sample_ids": [sample.sample_id for sample in samples],
        "source_groups": sorted({sample.source_group_id for sample in samples}),
        "labels": [IMAGE_CLASSES[value] for value in truth],
        "predicted": [IMAGE_CLASSES[value] for value in predicted],
        "tamper_probabilities": [round(float(value), 8) for value in scores],
        "threshold": threshold.value,
        "confusion_matrix_labels": target_names,
        "confusion_matrix": confusion_matrix(truth, predicted, labels=[0, 1]).tolist(),
        "per_class": per_class,
        "macro_f1": round(float(report["macro avg"]["f1-score"]), 6),
        "pr_auc": round(float(auc(recall, precision)), 6),
        "roc_auc": None if roc_auc is None else round(roc_auc, 6),
        "calibration": _calibration(truth, scores),
    }


def _augmentation(tf: Any) -> Any:
    layers = tf.keras.layers
    return tf.keras.Sequential(
        [
            layers.RandomRotation(0.02, seed=IMAGE_RANDOM_SEED),
            layers.RandomZoom(0.05, 0.05, seed=IMAGE_RANDOM_SEED + 1),
            layers.RandomContrast(0.08, seed=IMAGE_RANDOM_SEED + 2),
            layers.RandomTranslation(0.02, 0.02, seed=IMAGE_RANDOM_SEED + 3),
        ],
        name="training_only_augmentation",
    )


def build_image_model(*, pretrained: bool = True) -> tuple[Any, Any]:
    """Build the exact MobileNetV3Small graph; this does not fit any data."""

    tf = _tensorflow()
    tf.keras.utils.set_random_seed(IMAGE_RANDOM_SEED)
    with contextlib.suppress(AttributeError, RuntimeError):
        tf.config.experimental.enable_op_determinism()
    inputs = tf.keras.Input(
        shape=(IMAGE_INPUT_HEIGHT, IMAGE_INPUT_WIDTH, IMAGE_INPUT_CHANNELS), name="receipt_rgb"
    )
    augmented = _augmentation(tf)(inputs)
    backbone = tf.keras.applications.MobileNetV3Small(
        input_shape=(IMAGE_INPUT_HEIGHT, IMAGE_INPUT_WIDTH, IMAGE_INPUT_CHANNELS),
        include_top=False,
        include_preprocessing=False,
        weights="imagenet" if pretrained else None,
        name="mobilenet_v3_small_backbone",
    )
    backbone.trainable = False
    features = backbone(augmented, training=False)
    pooled = tf.keras.layers.GlobalAveragePooling2D(name="global_pool")(features)
    regularised = tf.keras.layers.Dropout(0.2, seed=IMAGE_RANDOM_SEED, name="head_dropout")(pooled)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid", name="tamper_probability")(regularised)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="momo_fdvs_image_tamper")
    return model, backbone


def _compile(model: Any, *, learning_rate: float) -> None:
    tf = _tensorflow()
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="binary_crossentropy",
        metrics=[
            tf.keras.metrics.BinaryAccuracy(name="accuracy"),
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
            tf.keras.metrics.AUC(curve="PR", name="pr_auc"),
        ],
    )


def _arrays(samples: Sequence[ImageSample]) -> tuple[np.ndarray, np.ndarray]:
    if not samples:
        raise ImageModelError("image partition is empty")
    try:
        features = np.stack([preprocess_image_path(sample.path) for sample in samples])
    except ImageDatasetError as exc:
        raise ImageModelError(str(exc)) from exc
    labels = np.asarray([sample.label_index for sample in samples], dtype=np.float32)
    return features, labels


def _predict_probabilities(model: Any, features: np.ndarray) -> list[float]:
    raw = np.asarray(model.predict(features, verbose=0), dtype=float)
    if raw.shape != (len(features), 1):
        raise ImageModelError("image model returned an invalid output shape")
    scores = raw[:, 0]
    if not np.isfinite(scores).all() or bool(((scores < 0) | (scores > 1)).any()):
        raise ImageModelError("image model returned an invalid probability")
    return [float(value) for value in scores]


def load_and_verify_image_artifact(
    path: Path, *, expected_sha256: str, expected_schema_hash: str
) -> Any:
    """Verify bytes and the canonical input contract before loading a trusted Keras model."""

    if path.suffix != ".keras" or not path.is_file():
        raise ImageModelError("image artifact must be an existing .keras file")
    if expected_schema_hash != IMAGE_PREPROCESSING_SCHEMA_HASH:
        raise ImageModelError("image preprocessing schema hash does not match the runtime")
    if sha256_file(path) != expected_sha256:
        raise ImageModelError("image artifact SHA-256 verification failed")
    tf = _tensorflow()
    try:
        model = tf.keras.models.load_model(path, compile=False, safe_mode=True)
    except Exception as exc:
        raise ImageModelError("verified image artifact could not be loaded") from exc
    input_shape = tuple(model.input_shape)
    output_shape = tuple(model.output_shape)
    if input_shape != (None, IMAGE_INPUT_HEIGHT, IMAGE_INPUT_WIDTH, IMAGE_INPUT_CHANNELS):
        raise ImageModelError("image artifact input shape does not match the runtime")
    if output_shape != (None, 1):
        raise ImageModelError("image artifact output shape does not match the runtime")
    return model


def benchmark_cpu_inference(
    model: Any, feature: np.ndarray, *, iterations: int = 30
) -> dict[str, object]:
    if iterations < 3:
        raise ImageModelError("latency benchmark requires at least three iterations")
    batch = feature[np.newaxis, ...]
    model.predict(batch, verbose=0)
    durations: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        model.predict(batch, verbose=0)
        durations.append((time.perf_counter() - started) * 1000)
    ordered = sorted(durations)
    p95_index = min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)
    return {
        "device": "CPU",
        "iterations": iterations,
        "median_ms": round(statistics.median(durations), 3),
        "p95_ms": round(ordered[p95_index], 3),
    }


def _write_confusion_matrix(path: Path, matrix: Sequence[Sequence[int]]) -> None:
    image = Image.new("RGB", (720, 560), "white")
    draw = ImageDraw.Draw(image)
    draw.text((36, 28), "P12 controlled held-out confusion matrix", fill="black")
    for index, label in enumerate(IMAGE_CLASSES):
        draw.text((265 + index * 190, 100), f"Pred {label}", fill="black")
        draw.text((30, 210 + index * 150), f"True {label}", fill="black")
    for row in range(2):
        for column in range(2):
            left = 260 + column * 190
            top = 170 + row * 150
            draw.rectangle((left, top, left + 150, top + 110), outline="black", width=2)
            draw.text((left + 65, top + 45), str(matrix[row][column]), fill="black")
    image.save(path, format="PNG")


def train_and_package_image_model(
    *,
    manifest_path: Path,
    dataset_root: Path,
    output_dir: Path,
    model_version: str,
    training_commit_sha: str,
) -> ImageTrainingOutputs:
    """Fit/evaluate once and package a private Keras artifact; execute only in Colab."""

    if not SHA_PATTERN.fullmatch(training_commit_sha):
        raise ImageModelError("training_commit_sha must be a full lowercase Git SHA")
    manifest = load_manifest(manifest_path)
    samples = governed_image_samples(manifest, root=dataset_root)
    partitions = {
        split: tuple(sample for sample in samples if sample.split == split)
        for split in ("train", "validation", "test")
    }
    train_x, train_y = _arrays(partitions["train"])
    validation_x, validation_y = _arrays(partitions["validation"])
    test_x, test_y = _arrays(partitions["test"])
    tf = _tensorflow()
    model, backbone = build_image_model(pretrained=True)
    _compile(model, learning_rate=0.001)
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = output_dir / "best-image-checkpoint.keras"
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            checkpoint, monitor="val_pr_auc", mode="max", save_best_only=True
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_pr_auc", mode="max", patience=5, restore_best_weights=True
        ),
    ]
    weights = class_weights([int(value) for value in train_y])
    head_history = model.fit(
        train_x,
        train_y,
        validation_data=(validation_x, validation_y),
        epochs=20,
        batch_size=4,
        shuffle=True,
        class_weight=weights,
        callbacks=callbacks,
        verbose=2,
    )
    backbone.trainable = True
    for layer in backbone.layers[:-20]:
        layer.trainable = False
    _compile(model, learning_rate=0.00001)
    fine_history = model.fit(
        train_x,
        train_y,
        validation_data=(validation_x, validation_y),
        epochs=10,
        batch_size=4,
        shuffle=True,
        class_weight=weights,
        callbacks=callbacks,
        verbose=2,
    )
    selected = tf.keras.models.load_model(checkpoint, compile=False, safe_mode=True)
    validation_probabilities = _predict_probabilities(selected, validation_x)
    threshold = select_image_threshold(
        [int(value) for value in validation_y], validation_probabilities
    )
    validation_report = evaluate_binary_partition(
        [int(value) for value in validation_y],
        validation_probabilities,
        threshold=threshold,
        samples=partitions["validation"],
    )
    test_probabilities = _predict_probabilities(selected, test_x)
    held_out = evaluate_binary_partition(
        [int(value) for value in test_y],
        test_probabilities,
        threshold=threshold,
        samples=partitions["test"],
    )
    artifact = output_dir / f"{model_version}.keras"
    selected.save(artifact)
    artifact_sha = sha256_file(artifact)
    latency = benchmark_cpu_inference(selected, test_x[0])
    acceptance_passed = bool(cast(float, held_out["macro_f1"]) >= MIN_ACCEPTABLE_MACRO_F1)
    report: dict[str, Any] = {
        "report_version": IMAGE_REPORT_VERSION,
        "dataset_scope": "controlled_synthetic_only",
        "model_name": IMAGE_MODEL_NAME,
        "model_version": model_version,
        "artifact": {
            "filename": artifact.name,
            "sha256": artifact_sha,
            "format": IMAGE_ARTIFACT_FORMAT,
            "committed_to_git": False,
        },
        "architecture_version": IMAGE_ARCHITECTURE_VERSION,
        "preprocessing_version": IMAGE_PREPROCESSING_VERSION,
        "preprocessing_schema_hash": IMAGE_PREPROCESSING_SCHEMA_HASH,
        "dataset_manifest_hash": manifest.manifest_hash,
        "split_hash": manifest.split_hash,
        "training_commit_sha": training_commit_sha,
        "random_seed": IMAGE_RANDOM_SEED,
        "framework_versions": runtime_fingerprint(),
        "training_policy": training_policy(),
        "partition_groups": {
            split: sorted({sample.source_group_id for sample in partition})
            for split, partition in partitions.items()
        },
        "class_weights": {str(key): round(value, 6) for key, value in weights.items()},
        "history": {
            "head_epochs": len(head_history.epoch),
            "fine_tune_epochs": len(fine_history.epoch),
        },
        "threshold": threshold.as_dict(),
        "validation": validation_report,
        "held_out_test": held_out,
        "cpu_inference": latency,
        "acceptance_thresholds": {"macro_f1_minimum": MIN_ACCEPTABLE_MACRO_F1},
        "acceptance_passed": acceptance_passed,
        "limitations": [
            "Controlled/synthetic data only; no provider-wide or production claim is allowed.",
            "The held-out test partition has one source group and two images.",
            "Controlled edits do not represent the diversity or prevalence of natural fraud.",
            "Heatmaps are supporting attention diagnostics, not proof or edit localisation.",
        ],
    }
    report_path = output_dir / "image_evaluation_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    model_card_path = output_dir / "IMAGE_MODEL_CARD.md"
    model_card_path.write_text(
        "\n".join(
            [
                f"# Model Card — {model_version}",
                "",
                "Controlled MobileNetV3Small tamper detector. Human review is required.",
                "It must not be described as provider-wide, calibrated or production-ready.",
                "",
                f"- Training commit: `{training_commit_sha}`",
                f"- Artifact SHA-256: `{artifact_sha}`",
                f"- Preprocessing SHA-256: `{IMAGE_PREPROCESSING_SCHEMA_HASH}`",
                (
                    f"- Held-out samples/groups: `{held_out['sample_count']}` / "
                    f"`{held_out['source_group_count']}`"
                ),
                f"- Held-out macro F1: `{held_out['macro_f1']}`",
                f"- Threshold selected on validation: `{threshold.value}`",
                f"- CPU median/p95 ms: `{latency['median_ms']}` / `{latency['p95_ms']}`",
                "",
                "The evidence corpus contains only six generic controlled source groups.",
            ]
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    registry_payload = {
        "model_type": "IMAGE",
        "name": IMAGE_MODEL_NAME,
        "version": model_version,
        "artifact_uri": f"private://image/{artifact.name}",
        "artifact_sha256": artifact_sha,
        "input_schema_hash": IMAGE_PREPROCESSING_SCHEMA_HASH,
        "preprocessing_version": IMAGE_PREPROCESSING_VERSION,
        "framework_versions": report["framework_versions"],
        "metrics": {
            "scope": report["dataset_scope"],
            "acceptance_passed": acceptance_passed,
            "macro_f1": held_out["macro_f1"],
            "threshold": threshold.value,
            "cpu_inference": latency,
        },
        "dataset_manifest_hash": manifest.manifest_hash,
        "split_hash": manifest.split_hash,
        "training_commit_sha": training_commit_sha,
        "model_card_key": "docs/models/IMAGE_MODEL_CARD_CONTROLLED_V1.md",
    }
    registry_path = output_dir / "image_registry_payload.json"
    registry_path.write_text(
        json.dumps(registry_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    matrix_path = output_dir / "image_confusion_matrix.png"
    _write_confusion_matrix(
        matrix_path, cast(Sequence[Sequence[int]], held_out["confusion_matrix"])
    )
    return ImageTrainingOutputs(
        artifact_path=artifact,
        artifact_sha256=artifact_sha,
        report_path=report_path,
        model_card_path=model_card_path,
        registry_payload_path=registry_path,
        confusion_matrix_path=matrix_path,
        report=report,
    )
