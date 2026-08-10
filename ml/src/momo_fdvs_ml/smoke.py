"""Tiny deterministic, restart-safe smoke flow over fictitious repository fixtures."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final, cast

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.preprocessing import StandardScaler

from momo_fdvs_ml.colab import (
    ColabFoundationError,
    artifact_record,
    atomic_write_json,
    canonical_json_hash,
    complete_run,
    load_checkpoint,
    load_checkpoint_ledger,
    load_json_object,
    make_run_id,
    mark_interrupted_session,
    new_run_manifest,
    runtime_inventory,
    seed_runtime,
    sha256_file,
    start_session,
    sync_verified_file,
    utc_now,
    validate_run_manifest,
    write_checkpoint,
)
from momo_fdvs_ml.execution import ExecutionProfile, require_smoke_execution
from momo_fdvs_ml.feature_schema import STRUCTURED_FEATURE_SCHEMA_VERSION

SMOKE_FLOW_VERSION: Final = "colab-smoke-flow-v1"
SMOKE_SEED: Final = 20260810
TRANSACTION_FEATURES: Final = (
    "ocr_mean_confidence",
    "critical_correction_count",
    "ela_mean",
    "noise_regional_cv",
    "amount_match",
    "name_similarity",
    "verification_mismatch_count",
)
IMAGE_FEATURES: Final = (
    "mean_r",
    "mean_g",
    "mean_b",
    "std_luma",
    "horizontal_edge",
    "vertical_edge",
)
COMPONENT_ORDER: Final = ("transaction", "ocr", "image")


class SimulatedRuntimeLoss(RuntimeError):
    """Test-only interruption raised after a durable checkpoint is synchronized."""


@dataclass(frozen=True)
class SmokeOutputs:
    run_id: str
    manifest_path: Path
    report_path: Path
    bundle_path: Path
    prediction_digest: str
    resumed: bool


def _rounded(values: np.ndarray, digits: int = 12) -> list[object]:
    return cast(list[object], np.round(values.astype(float), digits).tolist())


def _softmax(scores: np.ndarray) -> np.ndarray:
    shifted = scores - np.max(scores, axis=1, keepdims=True)
    exponentials = np.exp(shifted)
    return cast(np.ndarray, exponentials / exponentials.sum(axis=1, keepdims=True))


def _export_linear_model(
    *,
    scaler: StandardScaler,
    classifier: LogisticRegression | SGDClassifier,
    features: Sequence[str],
) -> dict[str, object]:
    return {
        "features": list(features),
        "classes": [str(value) for value in classifier.classes_],
        "scaler_mean": _rounded(scaler.mean_),
        "scaler_scale": _rounded(scaler.scale_),
        "coefficients": _rounded(classifier.coef_),
        "intercepts": _rounded(classifier.intercept_),
    }


def _predict_exported(model: Mapping[str, object], values: np.ndarray) -> np.ndarray:
    mean = np.asarray(model["scaler_mean"], dtype=float)
    scale = np.asarray(model["scaler_scale"], dtype=float)
    coefficients = np.asarray(model["coefficients"], dtype=float)
    intercepts = np.asarray(model["intercepts"], dtype=float)
    scaled = (values - mean) / scale
    scores = scaled @ coefficients.T + intercepts
    if coefficients.shape[0] == 1:
        positive = 1.0 / (1.0 + np.exp(-scores[:, 0]))
        return np.column_stack((1.0 - positive, positive))
    return _softmax(scores)


def _transaction_component(repository_root: Path, *, seed: int) -> dict[str, object]:
    dataset_path = repository_root / "ml/data/controlled/structured_features.csv"
    frame = pd.read_csv(dataset_path)
    frame = frame[frame["split"].isin(["train", "validation"])].copy()
    if len(frame) > 1_000 or "test" in set(frame["split"]):
        raise ColabFoundationError("smoke transaction data crossed its bounded split policy")
    train = frame[frame["split"] == "train"].copy()
    validation = frame[frame["split"] == "validation"].copy()
    medians = train[list(TRANSACTION_FEATURES)].median(numeric_only=True).fillna(0.0)
    train_values = train[list(TRANSACTION_FEATURES)].fillna(medians).to_numpy(dtype=float)
    validation_values = validation[list(TRANSACTION_FEATURES)].fillna(medians).to_numpy(dtype=float)
    scaler = StandardScaler().fit(train_values)
    classifier = LogisticRegression(random_state=seed, max_iter=200, solver="lbfgs")
    classifier.fit(scaler.transform(train_values), train["label"].astype(str).to_numpy())
    expected = classifier.predict_proba(scaler.transform(validation_values))
    model = _export_linear_model(
        scaler=scaler, classifier=classifier, features=TRANSACTION_FEATURES
    )
    reloaded = _predict_exported(model, validation_values)
    if not np.allclose(expected, reloaded, rtol=0.0, atol=1e-9):
        raise ColabFoundationError("transaction smoke export/reload prediction drifted")
    predictions = [
        {
            "sample_id": str(sample_id),
            "probabilities": {
                str(label): round(float(probability), 8)
                for label, probability in zip(classifier.classes_, row, strict=True)
            },
        }
        for sample_id, row in zip(validation["sample_id"], reloaded, strict=True)
    ]
    return {
        "component_version": "smoke-transaction-linear-v1",
        "train_rows": len(train),
        "validation_rows": len(validation),
        "test_rows_accessed": 0,
        "model": model,
        "validation_predictions": predictions,
    }


def _ocr_component(repository_root: Path) -> dict[str, object]:
    truth = load_json_object(repository_root / "data/fixtures/ocr-truth.fixture.json")
    transcript = truth.get("full_transcript")
    if not isinstance(transcript, str) or "SYNTHETIC" not in transcript:
        raise ColabFoundationError("smoke OCR fixture must be explicitly synthetic")
    amount_field = truth.get("amount")
    reference_field = truth.get("reference")
    if not isinstance(amount_field, dict) or not isinstance(reference_field, dict):
        raise ColabFoundationError("smoke OCR truth fields are invalid")
    import re

    amount_match = re.search(r"GHS\s+([0-9]+(?:\.[0-9]{2})?)", transcript)
    reference_match = re.search(r"\b(DEMO-REF-[0-9]{4})\b", transcript)
    if amount_match is None or reference_match is None:
        raise ColabFoundationError("lightweight smoke OCR could not parse its fixture")
    parsed_amount = float(amount_match.group(1))
    parsed_reference = reference_match.group(1)
    if parsed_amount != amount_field.get("normalized") or parsed_reference != reference_field.get(
        "normalized"
    ):
        raise ColabFoundationError("lightweight smoke OCR disagrees with ground truth")
    return {
        "component_version": "smoke-ocr-regex-v1",
        "image_id": truth["image_id"],
        "parsed_amount": parsed_amount,
        "parsed_reference": parsed_reference,
        "ground_truth_match": True,
    }


def _image_features(path: Path) -> np.ndarray:
    with Image.open(path) as opened:
        rgb = np.asarray(opened.convert("RGB").resize((32, 32)), dtype=np.float64) / 255.0
    luma = rgb.mean(axis=2)
    return np.asarray(
        [
            rgb[:, :, 0].mean(),
            rgb[:, :, 1].mean(),
            rgb[:, :, 2].mean(),
            luma.std(),
            np.abs(np.diff(luma, axis=1)).mean(),
            np.abs(np.diff(luma, axis=0)).mean(),
        ],
        dtype=float,
    )


def _image_component(repository_root: Path, *, seed: int) -> dict[str, object]:
    root = repository_root / "ml/data/controlled"
    rows: list[dict[str, str]] = []
    with (root / "manifest.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["split"] in {"train", "validation"}:
                rows.append(dict(row))
    if len(rows) > 20 or any(row["split"] == "test" for row in rows):
        raise ColabFoundationError("smoke image data crossed its bounded split policy")
    train = [row for row in rows if row["split"] == "train"]
    validation = [row for row in rows if row["split"] == "validation"]
    train_values = np.stack([_image_features(root / row["relative_path"]) for row in train])
    validation_values = np.stack(
        [_image_features(root / row["relative_path"]) for row in validation]
    )
    train_labels = np.asarray([row["label"] for row in train], dtype=str)
    scaler = StandardScaler().fit(train_values)
    classifier = SGDClassifier(
        loss="log_loss",
        random_state=seed,
        max_iter=1,
        tol=None,
        shuffle=False,
    )
    classifier.fit(scaler.transform(train_values), train_labels)
    expected = classifier.predict_proba(scaler.transform(validation_values))
    model = _export_linear_model(scaler=scaler, classifier=classifier, features=IMAGE_FEATURES)
    reloaded = _predict_exported(model, validation_values)
    if not np.allclose(expected, reloaded, rtol=0.0, atol=1e-9):
        raise ColabFoundationError("image smoke export/reload prediction drifted")
    predictions = [
        {
            "sample_id": row["sample_id"],
            "probabilities": {
                str(label): round(float(probability), 8)
                for label, probability in zip(classifier.classes_, values, strict=True)
            },
        }
        for row, values in zip(validation, reloaded, strict=True)
    ]
    return {
        "component_version": "smoke-image-linear-one-epoch-v1",
        "train_images": len(train),
        "validation_images": len(validation),
        "epochs": 1,
        "test_images_accessed": 0,
        "model": model,
        "validation_predictions": predictions,
    }


def _component_counts(repository_root: Path) -> tuple[int, int]:
    transaction_frame = pd.read_csv(
        repository_root / "ml/data/controlled/structured_features.csv",
        usecols=["split"],
    )
    transaction_rows = int(transaction_frame["split"].isin(["train", "validation"]).sum())
    with (repository_root / "ml/data/controlled/manifest.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        image_count = sum(
            1 for row in csv.DictReader(handle) if row["split"] in {"train", "validation"}
        )
    return transaction_rows, image_count


def _checkpoint_summary(entry: Mapping[str, object]) -> dict[str, object]:
    return {
        "checkpoint_id": entry["checkpoint_id"],
        "sha256": entry["sha256"],
        "bytes": entry["bytes"],
    }


def _latest_checkpoint_id(checkpoint_root: Path, run_id: str) -> str | None:
    ledger = load_checkpoint_ledger(checkpoint_root, run_id=run_id)
    entries = ledger["entries"]
    assert isinstance(entries, list)
    if not entries or not isinstance(entries[-1], dict):
        return None
    checkpoint_id = entries[-1].get("checkpoint_id")
    return checkpoint_id if isinstance(checkpoint_id, str) else None


def run_smoke_flow(
    *,
    repository_root: Path,
    vm_root: Path,
    drive_root: Path,
    git_state: Mapping[str, object],
    notebook: str,
    run_id: str | None = None,
    seed: int = SMOKE_SEED,
    started_at: datetime | None = None,
    stop_after_checkpoint: str | None = None,
) -> SmokeOutputs:
    """Run or resume the bounded smoke flow and emit verified durable artifacts."""

    if stop_after_checkpoint is not None and stop_after_checkpoint not in COMPONENT_ORDER:
        raise ColabFoundationError("unknown simulated stop checkpoint")
    start_time = utc_now() if started_at is None else started_at
    commit = git_state.get("commit")
    if not isinstance(commit, str):
        raise ColabFoundationError("smoke Git state must contain a commit")
    run_id = (
        make_run_id("smoke-foundation", commit, seed, started_at=start_time)
        if run_id is None
        else run_id
    )
    vm_run_root = vm_root / "runs" / run_id
    drive_run_root = drive_root / "runs" / run_id
    vm_checkpoints = vm_root / "checkpoints" / run_id
    drive_checkpoints = drive_root / "checkpoints" / run_id
    manifest_path = drive_run_root / "run_manifest.json"
    vm_run_root.mkdir(parents=True, exist_ok=True)
    drive_run_root.mkdir(parents=True, exist_ok=True)
    vm_checkpoints.mkdir(parents=True, exist_ok=True)
    drive_checkpoints.mkdir(parents=True, exist_ok=True)

    transaction_rows, image_count = _component_counts(repository_root)
    require_smoke_execution(
        ExecutionProfile.SMOKE,
        transaction_rows=transaction_rows,
        image_count=image_count,
        epochs=1,
        uses_locked_test=False,
    )
    seed_runtime(seed)
    dataset_report = load_json_object(repository_root / "ml/data/controlled/dataset_report.json")
    dependency_lock = repository_root / "ml/requirements-runtime.lock"
    config = {
        "flow_version": SMOKE_FLOW_VERSION,
        "profile": "smoke",
        "transaction_rows": transaction_rows,
        "image_count": image_count,
        "epochs": 1,
        "uses_locked_test": False,
    }

    resumed = manifest_path.is_file()
    if resumed:
        manifest = load_json_object(manifest_path)
        validate_run_manifest(manifest)
        if manifest["run_id"] != run_id or manifest["git"] != dict(git_state):
            raise ColabFoundationError("resume request does not match the durable run identity")
        if manifest["status"] == "completed":
            raise ColabFoundationError("completed smoke run cannot be resumed")
        sessions = manifest["sessions"]
        assert isinstance(sessions, list)
        if sessions and isinstance(sessions[-1], dict) and sessions[-1]["outcome"] == "active":
            mark_interrupted_session(manifest, detected_at=start_time)
        latest_id = _latest_checkpoint_id(drive_checkpoints, run_id)
        resumed_hash: str | None = None
        if latest_id is not None:
            _, latest_entry = load_checkpoint(
                vm_checkpoints,
                run_id=run_id,
                checkpoint_id=latest_id,
                mirror_root=drive_checkpoints,
            )
            resumed_hash = str(latest_entry["sha256"])
        start_session(manifest, started_at=start_time, resumed_from_sha256=resumed_hash)
    else:
        manifest = new_run_manifest(
            run_id=run_id,
            profile=ExecutionProfile.SMOKE,
            git_state=git_state,
            notebook=notebook,
            inventory=runtime_inventory(),
            seed=seed,
            dependency_lock_path="ml/requirements-runtime.lock",
            dependency_lock_sha256=sha256_file(dependency_lock),
            dataset_manifest_sha256=str(dataset_report["manifest_hash"]),
            split_manifest_sha256=str(dataset_report["split_hash"]),
            config_sha256=canonical_json_hash(config),
            feature_schema_versions=[
                STRUCTURED_FEATURE_SCHEMA_VERSION,
                "smoke-image-statistics-v1",
                "smoke-ocr-regex-v1",
            ],
            started_at=start_time,
        )
        start_session(manifest, started_at=start_time, resumed_from_sha256=None)
    atomic_write_json(manifest_path, manifest)

    ledger = load_checkpoint_ledger(drive_checkpoints, run_id=run_id)
    entries = ledger["entries"]
    assert isinstance(entries, list)
    available_ids = {
        str(entry["checkpoint_id"])
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("checkpoint_id"), str)
    }
    component_results: dict[str, object] = {}
    for component in COMPONENT_ORDER:
        if component in available_ids:
            state, _ = load_checkpoint(
                vm_checkpoints,
                run_id=run_id,
                checkpoint_id=component,
                mirror_root=drive_checkpoints,
            )
            component_results[component] = state["result"]
            continue
        if component == "transaction":
            result = _transaction_component(repository_root, seed=seed)
        elif component == "ocr":
            result = _ocr_component(repository_root)
        else:
            result = _image_component(repository_root, seed=seed)
        component_results[component] = result
        entry = write_checkpoint(
            vm_checkpoints,
            run_id=run_id,
            checkpoint_id=component,
            state={"component": component, "result": result},
            created_at=utc_now(),
            mirror_root=drive_checkpoints,
        )
        checkpoints = manifest["checkpoints"]
        assert isinstance(checkpoints, list)
        checkpoints.append(_checkpoint_summary(entry))
        atomic_write_json(manifest_path, manifest)
        if stop_after_checkpoint == component:
            raise SimulatedRuntimeLoss(f"simulated loss after {component} checkpoint")

    prediction_payload = {
        "transaction": component_results["transaction"],
        "ocr": component_results["ocr"],
        "image": component_results["image"],
    }
    prediction_digest = canonical_json_hash(prediction_payload)
    bundle = {
        "schema_version": "smoke-bundle-v1",
        "flow_version": SMOKE_FLOW_VERSION,
        "run_id": run_id,
        "seed": seed,
        "components": component_results,
        "prediction_digest": prediction_digest,
        "promotable": False,
        "training_scope": "tiny_fictitious_smoke_only",
    }
    vm_bundle_path = vm_run_root / "smoke_bundle.json"
    bundle_hash = atomic_write_json(vm_bundle_path, bundle)
    durable_bundle_path = drive_run_root / "smoke_bundle.json"
    sync_verified_file(vm_bundle_path, durable_bundle_path, expected_sha256=bundle_hash)
    reloaded_bundle = load_json_object(durable_bundle_path)
    if reloaded_bundle != bundle:
        raise ColabFoundationError("durable smoke bundle reload changed content")

    report = {
        "schema_version": "smoke-report-v1",
        "flow_version": SMOKE_FLOW_VERSION,
        "run_id": run_id,
        "profile": "smoke",
        "prediction_digest": prediction_digest,
        "transaction_rows": transaction_rows,
        "image_count": image_count,
        "image_epochs": 1,
        "test_partition_accessed": False,
        "acquisition_executed": False,
        "full_training_executed": False,
        "promotable": False,
        "resumed": resumed,
    }
    vm_report_path = vm_run_root / "smoke_report.json"
    report_hash = atomic_write_json(vm_report_path, report)
    durable_report_path = drive_run_root / "smoke_report.json"
    sync_verified_file(vm_report_path, durable_report_path, expected_sha256=report_hash)
    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)
    artifacts.extend(
        [
            artifact_record("smoke_bundle", durable_bundle_path, relative_to=drive_run_root),
            artifact_record("smoke_report", durable_report_path, relative_to=drive_run_root),
        ]
    )
    complete_run(manifest, completed_at=utc_now())
    atomic_write_json(manifest_path, manifest)
    validate_run_manifest(load_json_object(manifest_path))
    if len(prediction_digest) != 64:
        raise ColabFoundationError("prediction digest invariant failed")
    return SmokeOutputs(
        run_id=run_id,
        manifest_path=manifest_path,
        report_path=durable_report_path,
        bundle_path=durable_bundle_path,
        prediction_digest=prediction_digest,
        resumed=resumed,
    )
